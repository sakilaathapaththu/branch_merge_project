"""Report queries over the MB_Consolidated views (read-only)."""
from datetime import date
from decimal import Decimal

from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import get_engine

ACC_TYPES = {
    "001": "Equity",
    "002": "Assets",
    "003": "Liabilities",
    "004": "System",
    "005": "Income",
    "006": "Expenses",
}


def _v(name: str) -> str:
    return f"[{get_settings().db_consolidated}].dbo.{name}"


def _money(x) -> float:
    return float(Decimal(x or 0) / get_settings().amount_divisor)


def _branch_filter(branch: str, params: dict, col: str = "BranchCode") -> str:
    if branch == "all":
        return ""
    params["branch"] = branch
    return f" AND {col} = :branch"


def _rows(sql: str, params: dict) -> list[dict]:
    with get_engine().connect() as conn:
        return [dict(r._mapping) for r in conn.execute(text(sql), params)]


def _sort_heads(params_branch: str) -> dict[str, str]:
    """Level-2 sort-code headings (identical in both branches)."""
    rows = _rows(
        f"SELECT DISTINCT SortCode, FullDesc FROM {_v('vw_GLSortCodes')} WHERE LevelNumber = 2",
        {},
    )
    return {r["SortCode"]: r["FullDesc"] for r in rows}


def gl_accounts(branch: str) -> list[dict]:
    params: dict = {}
    sql = (
        f"SELECT BranchCode, GlAcc, ExpGlAcc, FullTitle, SortAcc, LevelNumber, CaluieType "
        f"FROM {_v('vw_GLAccounts')} WHERE Closed = 0" + _branch_filter(branch, params)
        + " ORDER BY GlAcc, BranchCode"
    )
    return [
        {
            "branch": r["BranchCode"],
            "glAcc": r["GlAcc"],
            "code": r["ExpGlAcc"],
            "title": r["FullTitle"],
            "sortCode": r["SortAcc"],
            "level": r["LevelNumber"],
            "type": ACC_TYPES.get(r["CaluieType"], r["CaluieType"]),
        }
        for r in _rows(sql, params)
    ]


def _balances(as_of: date, branch: str) -> list[dict]:
    params = {"y": str(as_of.year), "m": as_of.month}
    sql = (
        f"SELECT BranchCode, GlAcc, ExpGlAcc, FullTitle, SortAcc, AccType, ClosingBal "
        f"FROM {_v('vw_GLBalances')} WHERE FinYear = :y AND MonthNo = :m"
        + _branch_filter(branch, params)
    )
    return _rows(sql, params)


def _by_account(rows: list[dict], amount_key: str) -> list[dict]:
    """Sum rows across branches per GL account; HO title wins (titles differ for ~200 accounts)."""
    acc: dict[str, dict] = {}
    for r in sorted(rows, key=lambda r: r["BranchCode"]):
        a = acc.setdefault(
            r["GlAcc"],
            {
                "glAcc": r["GlAcc"],
                "code": r["ExpGlAcc"],
                "title": r["FullTitle"],
                "sortCode": r["SortAcc"],
                "accType": r["AccType"],
                "amount": Decimal(0),
                "byBranch": {},
            },
        )
        a["amount"] += Decimal(r[amount_key] or 0)
        a["byBranch"][r["BranchCode"]] = _money(r[amount_key])
    return sorted(acc.values(), key=lambda a: a["glAcc"])


def trial_balance(as_of: date, branch: str) -> dict:
    rows = _balances(as_of, branch)
    lines, dr, cr = [], Decimal(0), Decimal(0)
    for a in _by_account(rows, "ClosingBal"):
        if a["amount"] == 0:
            continue
        d = a["amount"] if a["amount"] > 0 else Decimal(0)
        c = -a["amount"] if a["amount"] < 0 else Decimal(0)
        dr, cr = dr + d, cr + c
        lines.append(
            {
                "glAcc": a["glAcc"],
                "code": a["code"],
                "title": a["title"],
                "type": ACC_TYPES.get(a["accType"], a["accType"]),
                "debit": _money(d),
                "credit": _money(c),
                "byBranch": a["byBranch"],
            }
        )
    return {
        "asOf": as_of.isoformat(),
        "branch": branch,
        "lines": lines,
        "totalDebit": _money(dr),
        "totalCredit": _money(cr),
        "balanced": dr == cr,
    }


def _grouped(accounts: list[dict], types: tuple[str, ...], sign: int, heads: dict) -> list[dict]:
    groups: dict[str, dict] = {}
    for a in accounts:
        if a["accType"] not in types or a["amount"] == 0:
            continue
        key = (a["sortCode"] or "")[:3]
        g = groups.setdefault(
            key,
            {"sortCode": key, "title": heads.get(key, key), "type": ACC_TYPES[a["accType"]],
             "amount": Decimal(0), "accounts": []},
        )
        amt = a["amount"] * sign
        g["amount"] += amt
        g["accounts"].append({"glAcc": a["glAcc"], "code": a["code"], "title": a["title"],
                              "amount": _money(amt)})
    out = []
    for g in sorted(groups.values(), key=lambda g: g["sortCode"]):
        g["amount"] = _money(g["amount"])
        out.append(g)
    return out


def balance_sheet(as_of: date, branch: str) -> dict:
    accounts = _by_account(_balances(as_of, branch), "ClosingBal")
    heads = _sort_heads(branch)
    total = lambda ts: sum((a["amount"] for a in accounts if a["accType"] in ts), Decimal(0))  # noqa: E731
    assets = total(("002",))
    liabilities = -total(("003",))
    equity = -total(("001",))
    profit = -total(("005", "006"))  # current-year result, not yet closed to equity
    return {
        "asOf": as_of.isoformat(),
        "branch": branch,
        "assets": _grouped(accounts, ("002",), 1, heads),
        "liabilities": _grouped(accounts, ("003",), -1, heads),
        "equity": _grouped(accounts, ("001",), -1, heads),
        "totalAssets": _money(assets),
        "totalLiabilities": _money(liabilities),
        "totalEquity": _money(equity),
        "currentYearProfit": _money(profit),
        "totalLiabilitiesAndEquity": _money(liabilities + equity + profit),
        "balanced": assets == liabilities + equity + profit,
    }


def profit_loss(date_from: date, date_to: date, branch: str) -> dict:
    params = {
        "f": date_from.year * 100 + date_from.month,
        "t": date_to.year * 100 + date_to.month,
    }
    sql = (
        f"SELECT BranchCode, GlAcc, ExpGlAcc, FullTitle, SortAcc, AccType, "
        f"SUM(MonthDr - MonthCr) AS Net FROM {_v('vw_GLBalances')} "
        f"WHERE AccType IN ('005','006') "
        f"AND CAST(FinYear AS int) * 100 + MonthNo BETWEEN :f AND :t"
        + _branch_filter(branch, params)
        + " GROUP BY BranchCode, GlAcc, ExpGlAcc, FullTitle, SortAcc, AccType"
    )
    accounts = _by_account(_rows(sql, params), "Net")
    heads = _sort_heads(branch)
    income = -sum((a["amount"] for a in accounts if a["accType"] == "005"), Decimal(0))
    expenses = sum((a["amount"] for a in accounts if a["accType"] == "006"), Decimal(0))
    return {
        "from": date_from.isoformat(),
        "to": date_to.isoformat(),
        "branch": branch,
        "note": "Whole calendar months; the open month is month-to-date.",
        "income": _grouped(accounts, ("005",), -1, heads),
        "expenses": _grouped(accounts, ("006",), 1, heads),
        "totalIncome": _money(income),
        "totalExpenses": _money(expenses),
        "netProfit": _money(income - expenses),
    }


def transactions(branch: str, date_from: date | None, date_to: date | None,
                 acc: str | None, page: int, size: int) -> dict:
    params: dict = {"off": (page - 1) * size, "size": size}
    where = "WHERE 1=1" + _branch_filter(branch, params)
    if date_from:
        where += " AND TrnDate >= :f"
        params["f"] = date_from
    if date_to:
        where += " AND TrnDate <= :t"
        params["t"] = date_to
    if acc:
        where += " AND Acc = :acc"
        params["acc"] = acc
    base = f"FROM {_v('vw_Transactions')} {where}"
    total = _rows(f"SELECT COUNT(*) AS n {base}", params)[0]["n"]
    rows = _rows(
        f"SELECT BranchCode, Recid, TrnDate, Acc, AppType, TrnType, TrnDesc, TrnAmt, BalAmt, CID, Tlr "
        f"{base} ORDER BY TrnDate DESC, Recid DESC OFFSET :off ROWS FETCH NEXT :size ROWS ONLY",
        params,
    )
    return {
        "page": page,
        "size": size,
        "total": total,
        "items": [
            {
                "branch": r["BranchCode"],
                "id": f"{r['BranchCode']}-{r['Recid']}",
                "date": r["TrnDate"].date().isoformat() if r["TrnDate"] else None,
                "acc": r["Acc"],
                "appType": r["AppType"],
                "trnType": r["TrnType"],
                "description": r["TrnDesc"],
                "amount": _money(r["TrnAmt"]),
                "balance": _money(r["BalAmt"]),
                "cid": r["CID"],
                "teller": r["Tlr"],
            }
            for r in rows
        ],
    }

"""Loan, arrears, deposit and customer-transaction reports.

Source tables (per branch database):
  T_LNACC   loan accounts (BalAmt outstanding, GrantedAmt, OduePriAmt overdue principal)
  T_LNINST  loan instalment schedule (Status '9' = paid)
  T_SVACC   savings accounts       T_TDACC  fixed (time) deposits
  T_PRPARMS product names (AppType + PrType -> FullDesc)
  T_RELACC + T_CIF  account -> customer
  T_TRNHIST customer transaction history
AccStatus '99' = closed.

Arrears days are derived from the oldest unpaid instalment due on or before the
system date, because MBWin's own LateDaysNo column is not maintained (always 0).
"""
from datetime import date, timedelta

from fastapi import HTTPException

from app.core.db import cached_query, query
from app.services.report import db, report, resolve_branches, short

_PRODUCTS = "(SELECT AppType, PrType, MAX(FullDesc) AS FullDesc FROM [{db}].dbo.T_PRPARMS GROUP BY AppType, PrType)"

BUCKETS = [(0, 0, "Current (not overdue)"), (1, 30, "1 – 30 days"), (31, 60, "31 – 60 days"),
           (61, 90, "61 – 90 days"), (91, 180, "91 – 180 days"), (181, 365, "181 – 365 days"),
           (366, 10**9, "Over 365 days")]


def system_date(code: str) -> date:
    """MBWin's current run date for the branch (falls back to today)."""
    r = cached_query(f"SELECT MAX(CurrRunDate) AS d FROM [{db(code)}].dbo.T_GLJL")
    d = r[0]["d"]
    return d.date() if d else date.today()


def _pivot(codes, per_code: dict[str, list[dict]], keys: list[tuple], measures: list[tuple]):
    """Merge per-branch rows on `keys`; add per-branch measure columns when several
    branches, plus totals. keys/measures: (field, label, type)."""
    multi = len(codes) > 1
    merged: dict[tuple, dict] = {}
    for c in codes:
        for r in per_code[c]:
            k = tuple(r[f] for f, _, _ in keys)
            row = merged.setdefault(k, {f: r[f] for f, _, _ in keys})
            for m, _, _ in measures:
                row[f"{m}_{c}"] = row.get(f"{m}_{c}", 0) + (r[m] or 0)
                row[m] = row.get(m, 0) + (r[m] or 0)
    rows = [merged[k] for k in sorted(merged, key=lambda k: tuple(str(x) for x in k))]
    cols = [{"key": f, "label": l, "type": t} for f, l, t in keys]
    if multi:
        for c in codes:
            cols += [{"key": f"{m}_{c}", "label": f"{short(c)} {l}", "type": t} for m, l, t in measures]
    cols += [{"key": m, "label": ("Total " + l) if multi else l, "type": t} for m, l, t in measures]
    total = {"_style": "total", keys[-1][0]: "TOTAL"}
    for r in rows:
        for k, v in r.items():
            if isinstance(v, (int, float)) and k not in {f for f, _, _ in keys}:
                total[k] = total.get(k, 0) + v
    return cols, rows, total


# ---------------------------------------------------------------- loans
def _loan_rows(code: str) -> list[dict]:
    return cached_query(f"""
        SELECT l.PrType AS prtype, COALESCE(p.FullDesc, 'Product ' + l.PrType) AS product,
               COUNT(*) AS n, SUM(l.GrantedAmt) AS granted, SUM(l.BalAmt) AS outstanding,
               SUM(CASE WHEN l.OduePriAmt > 0 THEN 1 ELSE 0 END) AS n_overdue,
               SUM(CASE WHEN l.OduePriAmt > 0 THEN l.OduePriAmt ELSE 0 END) AS overdue,
               SUM(l.AcrIntAmt) AS accrued
        FROM [{db(code)}].dbo.T_LNACC l
        LEFT JOIN {_PRODUCTS.format(db=db(code))} p ON p.AppType = l.AppType AND p.PrType = l.PrType
        WHERE l.AccStatus <> '99' AND l.BalAmt <> 0
        GROUP BY l.PrType, p.FullDesc""")


def loan_portfolio(branch: str) -> dict:
    codes = resolve_branches(branch)
    cols, rows, total = _pivot(
        codes, {c: _loan_rows(c) for c in codes},
        [("prtype", "Code", "text"), ("product", "Loan product", "text")],
        [("n", "Loans", "number"), ("granted", "Granted", "money"),
         ("outstanding", "Outstanding", "money"), ("overdue", "Overdue principal", "money"),
         ("accrued", "Accrued interest", "money")])
    share = total.get("outstanding") or 1
    for r in rows:
        r["share"] = r["outstanding"] / share * 100
    total["share"] = 100.0
    cols.append({"key": "share", "label": "% of portfolio", "type": "percent"})
    asof = ", ".join(f"{short(c)} {system_date(c).isoformat()}" for c in codes)
    return report("Loan Portfolio by Product", codes, cols, rows + [total], f"As at {asof}",
                  ["Active loans (status ≠ 99) with a non-zero balance."])


def _arrears_rows(code: str) -> list[dict]:
    return cached_query(f"""
        WITH od AS (
            SELECT Acc, Chd, MIN(DueDate) AS first_due
            FROM [{db(code)}].dbo.T_LNINST
            WHERE Status <> '9' AND DueDate <= :asof
            GROUP BY Acc, Chd)
        SELECT l.Acc AS acc, l.PrType AS prtype, COALESCE(p.FullDesc, l.PrType) AS product,
               l.BalAmt AS outstanding,
               CASE WHEN l.OduePriAmt > 0 THEN l.OduePriAmt ELSE 0 END AS overdue,
               od.first_due, ISNULL(DATEDIFF(day, od.first_due, :asof), 0) AS days,
               l.OpenDate AS opened, l.MatDate AS maturity, l.GrantedAmt AS granted,
               cust.name AS customer
        FROM [{db(code)}].dbo.T_LNACC l
        LEFT JOIN od ON od.Acc = l.Acc AND od.Chd = l.Chd
        LEFT JOIN {_PRODUCTS.format(db=db(code))} p ON p.AppType = l.AppType AND p.PrType = l.PrType
        OUTER APPLY (SELECT TOP 1 COALESCE(NULLIF(c.DisplayName, ''), c.Name1) AS name
                     FROM [{db(code)}].dbo.T_RELACC r
                     JOIN [{db(code)}].dbo.T_CIF c ON c.CID = r.CID
                     WHERE r.ACC = l.Acc ORDER BY r.Type) cust
        WHERE l.AccStatus <> '99' AND l.BalAmt > 0""", {"asof": system_date(code)})


def arrears_ageing(branch: str) -> dict:
    codes = resolve_branches(branch)
    per = {}
    for c in codes:
        rows = []
        data = _arrears_rows(c)
        for lo, hi, label in BUCKETS:
            sel = [r for r in data if lo <= r["days"] <= hi]
            rows.append({"bucket": label, "lo": lo, "n": len(sel),
                         "outstanding": sum(r["outstanding"] for r in sel),
                         "overdue": sum(r["overdue"] for r in sel)})
        per[c] = rows
    cols, rows, total = _pivot(codes, per, [("lo", "", "text"), ("bucket", "Days in arrears", "text")],
                               [("n", "Loans", "number"), ("outstanding", "Outstanding", "money")])
    cols = cols[1:]  # hide sort key
    port = total.get("outstanding") or 1
    for r in rows:
        r["share"] = r["outstanding"] / port * 100
    total["share"] = 100.0
    cols.append({"key": "share", "label": "% of portfolio", "type": "percent"})
    par = lambda d: sum(r["outstanding"] for r in rows if r["lo"] > d) / port * 100  # noqa: E731
    notes = [f"PAR > 30 days: {par(30):.2f}%   ·   PAR > 90 days: {par(90):.2f}%",
             "Days in arrears = system date − oldest unpaid instalment due date (from T_LNINST). "
             "Reconcile with MBWin's arrears report before relying on it."]
    asof = ", ".join(f"{short(c)} {system_date(c).isoformat()}" for c in codes)
    return report("Loan Arrears Ageing (Portfolio at Risk)", codes, cols, rows + [total],
                  f"As at {asof}", notes)


def arrears_list(branch: str, min_days: int = 31, limit: int = 1000) -> dict:
    codes = resolve_branches(branch)
    rows = []
    for c in codes:
        rows += [{**r, "branch": short(c)} for r in _arrears_rows(c) if r["days"] >= min_days]
    rows.sort(key=lambda r: (-r["days"], -r["outstanding"]))
    notes = [f"{len(rows):,} loans with {min_days}+ days in arrears."]
    if len(rows) > limit:
        notes.append(f"Showing the first {limit:,}.")
    total = {"_style": "total", "customer": "TOTAL",
             "outstanding": sum(r["outstanding"] for r in rows),
             "overdue": sum(r["overdue"] for r in rows)}
    for r in rows:
        for k in ("first_due", "opened", "maturity"):
            r[k] = r[k].date().isoformat() if r[k] else ""
    cols = ([{"key": "branch", "label": "Branch", "type": "text"}] if len(codes) > 1 else []) + [
        {"key": "acc", "label": "Account", "type": "text"},
        {"key": "customer", "label": "Customer", "type": "text"},
        {"key": "product", "label": "Product", "type": "text"},
        {"key": "opened", "label": "Opened", "type": "date"},
        {"key": "maturity", "label": "Maturity", "type": "date"},
        {"key": "granted", "label": "Granted", "type": "money"},
        {"key": "outstanding", "label": "Outstanding", "type": "money"},
        {"key": "overdue", "label": "Overdue principal", "type": "money"},
        {"key": "first_due", "label": "Oldest unpaid due", "type": "date"},
        {"key": "days", "label": "Days", "type": "number"},
    ]
    return report("Loans in Arrears", codes, cols, rows[:limit] + [total],
                  f"{min_days}+ days overdue", notes)


# ---------------------------------------------------------------- deposits
def _deposit_rows(code: str) -> list[dict]:
    p = _PRODUCTS.format(db=db(code))
    sql = """
        SELECT '{kind}' AS kind, a.PrType AS prtype, COALESCE(p.FullDesc, 'Product ' + a.PrType) AS product,
               COUNT(*) AS n, SUM(a.BalAmt) AS balance, SUM(a.BalAmt * a.IntRate) AS bal_rate,
               SUM(a.AcrIntAmt) AS accrued
        FROM [{db}].dbo.{table} a
        LEFT JOIN {p} p ON p.AppType = a.AppType AND p.PrType = a.PrType
        WHERE a.AccStatus <> '99'
        GROUP BY a.PrType, p.FullDesc"""
    return cached_query(
        sql.format(kind="Savings", db=db(code), table="T_SVACC", p=p)
        + " UNION ALL "
        + sql.format(kind="Fixed deposits", db=db(code), table="T_TDACC", p=p))


def deposits(branch: str) -> dict:
    codes = resolve_branches(branch)
    cols, rows, total = _pivot(
        codes, {c: _deposit_rows(c) for c in codes},
        [("kind", "Type", "text"), ("prtype", "Code", "text"), ("product", "Deposit product", "text")],
        [("n", "Accounts", "number"), ("balance", "Balance", "money"),
         ("accrued", "Accrued interest", "money"), ("bal_rate", "", "money")])
    cols = [c for c in cols if not c["key"].startswith("bal_rate")]
    for r in rows + [total]:
        r["rate"] = r["bal_rate"] / r["balance"] if r.get("balance") else None
    cols.append({"key": "rate", "label": "Avg rate %", "type": "percent"})

    out, kinds = [], {}
    for r in rows:
        kinds.setdefault(r["kind"], []).append(r)
    for kind, items in kinds.items():
        out.append({"kind": kind, "_style": "subheading"})
        out += items
        sub = {"product": f"Total {kind}", "_style": "subtotal"}
        for k in items[0]:
            if k not in ("kind", "prtype", "product", "rate") and isinstance(items[0][k], (int, float)):
                sub[k] = sum(i.get(k) or 0 for i in items)
        sub["rate"] = sub["bal_rate"] / sub["balance"] if sub.get("balance") else None
        out.append(sub)
    total["product"], total["prtype"] = "TOTAL DEPOSITS", ""
    asof = ", ".join(f"{short(c)} {system_date(c).isoformat()}" for c in codes)
    return report("Deposit Portfolio by Product", codes, cols, out + [total], f"As at {asof}",
                  ["Open accounts (status ≠ 99). Average rate is balance-weighted."])


# ---------------------------------------------------------------- transactions
def transactions(branch: str, date_from: date, date_to: date, acc: str | None, limit: int = 2000) -> dict:
    codes = resolve_branches(branch)
    if date_from > date_to:
        raise HTTPException(400, "date_from must be before date_to")
    if not acc and (date_to - date_from) > timedelta(days=31):
        raise HTTPException(400, "Without an account number the date range is limited to 31 days")
    if acc and not acc.isdigit():
        raise HTTPException(400, "Account number must be digits")
    rows = []
    for c in codes:
        rows += [{**r, "branch": short(c)} for r in query(f"""
            SELECT TOP (:lim) TrnDate AS d, Acc AS acc, Trn AS trn, TrnDesc AS descr, TrnAmt AS amount,
                   BalAmt AS balance, Tlr AS teller, GLCode AS gl, CID AS cid
            FROM [{db(c)}].dbo.T_TRNHIST
            WHERE TrnDate BETWEEN :f AND :t {"AND Acc = :acc" if acc else ""}
            ORDER BY TrnDate, Trn""", {"lim": limit + 1, "f": date_from, "t": date_to, "acc": acc})]
    rows.sort(key=lambda r: (r["d"], r["branch"], r["trn"] or ""))
    notes = []
    if len(rows) > limit:
        notes.append(f"Showing the first {limit:,} transactions; narrow the filter.")
        rows = rows[:limit]
    for r in rows:
        r["d"] = r["d"].date().isoformat()
    cols = ([{"key": "branch", "label": "Branch", "type": "text"}] if len(codes) > 1 else []) + [
        {"key": "d", "label": "Date", "type": "date"},
        {"key": "acc", "label": "Account", "type": "text"},
        {"key": "trn", "label": "Trn #", "type": "text"},
        {"key": "descr", "label": "Description", "type": "text"},
        {"key": "amount", "label": "Amount", "type": "money"},
        {"key": "balance", "label": "Balance after", "type": "money"},
        {"key": "teller", "label": "Teller", "type": "text"},
        {"key": "gl", "label": "GL", "type": "text"},
        {"key": "cid", "label": "Customer ID", "type": "text"},
    ]
    if len(codes) > 1:
        notes.append("Account numbers and customer IDs are per branch: the same number can exist in both.")
    return report("Customer Transactions", codes, cols, rows,
                  f"{date_from.isoformat()} to {date_to.isoformat()}" + (f" · Account {acc}" if acc else ""),
                  notes)


# ---------------------------------------------------------------- dashboard helpers
def portfolio_kpis(code: str) -> dict:
    ln = _loan_rows(code)
    ar = _arrears_rows(code)
    dep = _deposit_rows(code)
    cif = cached_query(f"SELECT COUNT(*) AS n FROM [{db(code)}].dbo.T_CIF")[0]["n"]
    outstanding = sum(r["outstanding"] for r in ln)
    return {
        "loans_count": sum(r["n"] for r in ln),
        "loans_outstanding": outstanding,
        "par30_amount": sum(r["outstanding"] for r in ar if r["days"] > 30),
        "savings": sum(r["balance"] or 0 for r in dep if r["kind"] == "Savings"),
        "fixed_deposits": sum(r["balance"] or 0 for r in dep if r["kind"] != "Savings"),
        "deposit_accounts": sum(r["n"] for r in dep),
        "customers": cif,
        "as_of": system_date(code).isoformat(),
    }

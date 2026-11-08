"""General-ledger reports built from MBWin's GL master tables.

Source tables (per branch database):
  T_GLAC      current financial year: per GL opening balance (OBalAmt) and
              debits/credits per month (DebitsAmt1..12 / CreditsAmt1..12)
  T_GLACHIST  same structure for previous financial years
  T_GLSC      report headings (SortCode -> FullDesc), e.g. 315 = LOANS AND ADVANCES
  T_GlJlHIST + T_GLJL   journal lines (history + current day) for the GL ledger

Verified on the 31-Oct-2026 backups: CBalAmt = OBalAmt + Debits - Credits for every
GL, monthly columns sum to the yearly totals, and journal lines reconcile to T_GLAC.
Sign convention: debit balances positive, credit balances negative.
CaluieType: 001 equity, 002 assets, 003 liabilities, 004 suspense, 005 income, 006 expenses.
"""
import re
from dataclasses import dataclass
from datetime import date

from fastapi import HTTPException

from app.core.config import get_settings
from app.core.db import cached_query, query
from app.services.report import amount_columns, db, report, resolve_branches, short

EQUITY, ASSET, LIAB, SUSPENSE, INCOME, EXPENSE = "001", "002", "003", "004", "005", "006"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_MCOLS = ", ".join(f"DebitsAmt{i}, CreditsAmt{i}" for i in range(1, 13))
_GL_RE = re.compile(r"^\d{3,12}$")


@dataclass
class GL:
    gl: str
    title: str
    sort: str
    ctype: str
    ob: float
    dr: list[float]
    cr: list[float]

    def balance(self, month: int) -> float:
        """Closing balance at the end of `month` (1-12)."""
        return self.ob + sum(self.dr[:month]) - sum(self.cr[:month])

    def movement(self, m_from: int, m_to: int) -> float:
        return sum(self.dr[m_from - 1:m_to]) - sum(self.cr[m_from - 1:m_to])


def current_year(code: str) -> int:
    r = cached_query(f"SELECT MAX(FinYear) AS y FROM [{db(code)}].dbo.T_GLAC")
    return int(r[0]["y"])


def load_gl(code: str, year: int) -> dict[str, GL]:
    table = "T_GLAC" if year == current_year(code) else "T_GLACHIST"
    rows = cached_query(
        f"SELECT GlAcc, FullTitle, SortAcc, CaluieType, OBalAmt, {_MCOLS} "
        f"FROM [{db(code)}].dbo.{table} WHERE FinYear = :y",
        {"y": year},
    )
    return {
        r["GlAcc"]: GL(
            gl=r["GlAcc"],
            title=r["FullTitle"] or "",
            sort=str(r["SortAcc"] or "").strip(),
            ctype=r["CaluieType"] or "",
            ob=r["OBalAmt"] or 0.0,
            dr=[r[f"DebitsAmt{i}"] or 0.0 for i in range(1, 13)],
            cr=[r[f"CreditsAmt{i}"] or 0.0 for i in range(1, 13)],
        )
        for r in rows
    }


def headings(codes: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for c in reversed(codes):  # first branch (HO) wins on differing names
        for r in cached_query(f"SELECT SortCode, FullDesc FROM [{db(c)}].dbo.T_GLSC"):
            out[str(r["SortCode"]).strip()] = r["FullDesc"]
    return out


def periods() -> dict:
    codes = list(get_settings().branches)
    cur = current_year(codes[0])
    years = sorted(
        {cur}
        | {
            int(r["FinYear"])
            for r in cached_query(f"SELECT DISTINCT FinYear FROM [{db(codes[0])}].dbo.T_GLACHIST")
        },
        reverse=True,
    )
    last = 1
    for c in codes:
        for g in load_gl(c, cur).values():
            for i in range(12, 0, -1):
                if g.dr[i - 1] or g.cr[i - 1]:
                    last = max(last, i)
                    break
    return {"current_year": cur, "last_month": last, "years": years}


def _validate_period(year: int | None, month: int | None) -> tuple[int, int]:
    p = periods()
    year = year or p["current_year"]
    if year not in p["years"]:
        raise HTTPException(400, f"Year {year} not available")
    month = month or (p["last_month"] if year == p["current_year"] else 12)
    if not 1 <= month <= 12:
        raise HTTPException(400, "month must be 1-12")
    return year, month


class Ledger:
    """GL data for one or more branches with inter-branch eliminations."""

    def __init__(self, codes: list[str], year: int):
        self.codes = codes
        self.multi = len(codes) > 1
        self.data = {c: load_gl(c, year) for c in codes}
        self.gls = sorted(set().union(*(d.keys() for d in self.data.values())))
        groups = get_settings().elimination_groups
        # Only eliminate groups whose branches are all in scope.
        self.groups = [g for g in groups if all(b in codes for b, _ in g)] if self.multi else []
        self.elim = {pair for g in self.groups for pair in g}

    def info(self, gl: str) -> GL:
        for c in self.codes:
            if gl in self.data[c]:
                return self.data[c][gl]
        raise KeyError(gl)

    def amounts(self, gl: str, fn, sign: int = 1) -> dict[str, float]:
        vals = {}
        for c in self.codes:
            g = self.data[c].get(gl)
            vals[f"b{c}"] = sign * fn(g) if g else 0.0
        if not self.multi:
            return {"total": vals[f"b{self.codes[0]}"]}
        elim = -sum(vals[f"b{c}"] for c in self.codes if (c, gl) in self.elim)
        return {**vals, "elim": elim, "total": sum(vals.values()) + elim}

    def zero(self) -> dict[str, float]:
        keys = ([f"b{c}" for c in self.codes] + ["elim"] if self.multi else []) + ["total"]
        return dict.fromkeys(keys, 0.0)

    def elimination_notes(self, fn) -> list[str]:
        notes = []
        for g in self.groups:
            net = sum(fn(self.data[b][gl]) for b, gl in g if gl in self.data[b])
            names = " / ".join(f"{short(b)} {gl}" for b, gl in g)
            if abs(net) > 0.5:
                notes.append(f"⚠ Inter-branch accounts do not agree ({names}): difference {net:,.2f}")
            else:
                notes.append(f"Eliminated inter-branch accounts: {names}")
        return notes


def _add(a: dict, b: dict, sign: int = 1) -> dict:
    return {k: a.get(k, 0.0) + sign * b.get(k, 0.0) for k in a}


def _nonzero(a: dict) -> bool:
    return any(abs(v) >= 0.005 for v in a.values())


# ---------------------------------------------------------------- trial balance
def trial_balance(branch: str, year: int | None, month: int | None, show_zero: bool = False) -> dict:
    codes = resolve_branches(branch)
    year, month = _validate_period(year, month)
    L = Ledger(codes, year)
    fn = lambda g: g.balance(month)  # noqa: E731

    rows, tot = [], {**L.zero(), "debit": 0.0, "credit": 0.0}
    for gl in L.gls:
        a = L.amounts(gl, fn)
        if not show_zero and not _nonzero(a):
            continue
        t = a["total"]
        row = {"gl": gl, "title": L.info(gl).title, **a,
               "debit": t if t > 0 else 0.0, "credit": -t if t < 0 else 0.0}
        rows.append(row)
        tot = {k: tot[k] + row[k] for k in tot}
    rows.append({"gl": "", "title": "TOTAL", **tot, "_style": "total"})

    cols = [{"key": "gl", "label": "GL Code", "type": "text"},
            {"key": "title", "label": "Account", "type": "text"}]
    if L.multi:
        cols += amount_columns(codes)[:-1]  # branch columns + eliminations
    cols += [{"key": "debit", "label": "Debit", "type": "money"},
             {"key": "credit", "label": "Credit", "type": "money"}]

    diff = tot["debit"] - tot["credit"]
    notes = [f"⚠ Trial balance out of balance by {diff:,.2f}" if abs(diff) > 0.5
             else "Trial balance agrees (Debits = Credits)."]
    notes += L.elimination_notes(fn)
    if L.multi:
        notes.append("Branch columns show net balances (debit +, credit −).")
    return report("Trial Balance", codes, cols, rows,
                  f"As at end of {MONTHS[month - 1]} {year}", notes)


# ---------------------------------------------------------------- statements
def _section(L: Ledger, heads: dict, ctypes: set[str], fn, sign: int, detail: bool):
    groups: dict[str, list] = {}
    for gl in L.gls:
        g = L.info(gl)
        if g.ctype in ctypes:
            groups.setdefault(g.sort[:3], []).append((gl, g.title, L.amounts(gl, fn, sign)))
    rows, total = [], L.zero()
    for hk in sorted(groups):
        items = [i for i in groups[hk] if _nonzero(i[2])]
        if not items:
            continue
        sub = L.zero()
        for _, _, a in items:
            sub = _add(sub, a)
        label = heads.get(hk, hk)
        if detail:
            rows.append({"code": hk, "label": label, "_style": "subheading"})
            rows += [{"code": gl, "label": t, **a, "_style": "detail"} for gl, t, a in items]
            rows.append({"code": "", "label": f"Total {label.title()}", **sub, "_style": "subtotal"})
        else:
            rows.append({"code": hk, "label": label, **sub})
        total = _add(total, sub)
    return rows, total


def _statement_columns(codes):
    return [{"key": "code", "label": "Code", "type": "text"},
            {"key": "label", "label": "Description", "type": "text"}] + amount_columns(codes)


def balance_sheet(branch: str, year: int | None, month: int | None, detail: bool = False) -> dict:
    codes = resolve_branches(branch)
    year, month = _validate_period(year, month)
    L, heads = Ledger(codes, year), headings(codes)
    fn = lambda g: g.balance(month)  # noqa: E731

    rows = [{"label": "ASSETS", "_style": "heading"}]
    r, A = _section(L, heads, {ASSET}, fn, +1, detail)
    rows += r + [{"label": "TOTAL ASSETS", **A, "_style": "total"}]

    rows.append({"label": "LIABILITIES", "_style": "heading"})
    r, Li = _section(L, heads, {LIAB}, fn, -1, detail)
    rows += r + [{"label": "TOTAL LIABILITIES", **Li, "_style": "subtotal"}]

    rows.append({"label": "EQUITY", "_style": "heading"})
    r, E = _section(L, heads, {EQUITY}, fn, -1, detail)
    _, P = _section(L, heads, {INCOME, EXPENSE}, fn, -1, False)
    rows += r + [{"label": "Current year profit / (loss)", **P}]
    TE = _add(E, P)
    rows.append({"label": "TOTAL EQUITY", **TE, "_style": "subtotal"})

    _, S = _section(L, heads, {SUSPENSE}, fn, -1, False)
    TLE = _add(_add(Li, TE), S)
    if _nonzero(S):
        rows.append({"label": "Suspense & transitory accounts (net)", **S})
    rows.append({"label": "TOTAL LIABILITIES & EQUITY", **TLE, "_style": "total"})

    diff = A["total"] - TLE["total"]
    notes = [f"⚠ Balance sheet does not balance: difference {diff:,.2f}" if abs(diff) > 0.5
             else "Balance sheet balances (Assets = Liabilities + Equity)."]
    notes += L.elimination_notes(fn)
    return report("Balance Sheet (Statement of Financial Position)", codes,
                  _statement_columns(codes), rows,
                  f"As at end of {MONTHS[month - 1]} {year}", notes)


def income_statement(branch: str, year: int | None, from_month: int | None,
                     to_month: int | None, detail: bool = False) -> dict:
    codes = resolve_branches(branch)
    year, to_month = _validate_period(year, to_month)
    from_month = from_month or 1
    if not 1 <= from_month <= to_month:
        raise HTTPException(400, "from_month must be between 1 and to_month")
    L, heads = Ledger(codes, year), headings(codes)
    fn = lambda g: g.movement(from_month, to_month)  # noqa: E731

    rows = [{"label": "INCOME", "_style": "heading"}]
    r, I = _section(L, heads, {INCOME}, fn, -1, detail)
    rows += r + [{"label": "TOTAL INCOME", **I, "_style": "subtotal"}]
    rows.append({"label": "EXPENSES", "_style": "heading"})
    r, X = _section(L, heads, {EXPENSE}, fn, +1, detail)
    rows += r + [{"label": "TOTAL EXPENSES", **X, "_style": "subtotal"}]
    rows.append({"label": "NET PROFIT / (LOSS)", **_add(I, X, -1), "_style": "total"})

    period = (f"{MONTHS[from_month - 1]} – {MONTHS[to_month - 1]} {year}"
              if from_month != to_month else f"{MONTHS[to_month - 1]} {year}")
    return report("Income Statement (Profit & Loss)", codes, _statement_columns(codes), rows,
                  period, L.elimination_notes(fn))


# ---------------------------------------------------------------- GL ledger
def gl_accounts() -> list[dict]:
    codes = list(get_settings().branches)
    L = Ledger(codes, current_year(codes[0]))
    return [{"gl": gl, "title": L.info(gl).title} for gl in L.gls]


_LEDGER_SQL = """
SELECT d, jnl, line, descr, ref, dr, cr FROM (
  SELECT JnlDate AS d, JnlNumber AS jnl, LineNumber AS line, FullDesc AS descr, Ref AS ref,
         CASE WHEN DrGLAccTF = 'T' AND DrAcc = :gl THEN DrAmt ELSE 0 END AS dr,
         CASE WHEN CrGLAccTF = 'T' AND CrAcc = :gl THEN CrAmt ELSE 0 END AS cr
  FROM [{db}].dbo.T_GlJlHIST
  WHERE (DrAcc = :gl OR CrAcc = :gl) AND JnlDate BETWEEN :y0 AND :to
  UNION ALL
  SELECT CurrRunDate, JnlNumber, LineNumber, FullDesc, Ref,
         CASE WHEN DrGLAccTF = 'T' AND DrAcc = :gl THEN DrAmt ELSE 0 END,
         CASE WHEN CrGLAccTF = 'T' AND CrAcc = :gl THEN CrAmt ELSE 0 END
  FROM [{db}].dbo.T_GLJL
  WHERE (DrAcc = :gl OR CrAcc = :gl) AND CurrRunDate BETWEEN :y0 AND :to
) x WHERE dr <> 0 OR cr <> 0
ORDER BY d, jnl, line
"""
MAX_LEDGER_ROWS = 5000


def gl_ledger(branch: str, gl: str, date_from: date, date_to: date) -> dict:
    codes = resolve_branches(branch)
    if not _GL_RE.match(gl):
        raise HTTPException(400, "Invalid GL code")
    if date_from > date_to or date_from.year != date_to.year:
        raise HTTPException(400, "Dates must be in order and within one financial year")
    year = date_from.year
    y0 = date(year, 1, 1)

    opening, lines, title = 0.0, [], ""
    for c in codes:
        g = load_gl(c, year).get(gl)
        if g:
            title = title or g.title
            opening += g.ob
        for r in query(_LEDGER_SQL.format(db=db(c)), {"gl": gl, "y0": y0, "to": date_to}):
            d = r["d"].date() if hasattr(r["d"], "date") else r["d"]
            if d < date_from:
                opening += r["dr"] - r["cr"]
            else:
                lines.append({**r, "d": d, "branch": short(c)})
    lines.sort(key=lambda r: (r["d"], r["branch"], r["jnl"] or "", r["line"] or ""))

    notes = []
    if len(lines) > MAX_LEDGER_ROWS:
        notes.append(f"Showing first {MAX_LEDGER_ROWS:,} of {len(lines):,} lines; narrow the date range.")
    bal = opening
    rows = [{"date": date_from.isoformat(), "descr": "Opening balance", "balance": opening, "_style": "subtotal"}]
    dr_t = cr_t = 0.0
    for r in lines:
        bal += r["dr"] - r["cr"]
        dr_t += r["dr"]
        cr_t += r["cr"]
        if len(rows) <= MAX_LEDGER_ROWS:
            rows.append({"date": r["d"].isoformat(), "branch": r["branch"],
                         "jnl": f"{r['jnl'] or ''} {r['line'] or ''}".strip(),
                         "descr": r["descr"] or "", "ref": r["ref"] or "",
                         "debit": r["dr"], "credit": r["cr"], "balance": bal})
    rows.append({"date": date_to.isoformat(), "descr": "Closing balance",
                 "debit": dr_t, "credit": cr_t, "balance": bal, "_style": "total"})

    cols = [{"key": "date", "label": "Date", "type": "date"}]
    if len(codes) > 1:
        cols.append({"key": "branch", "label": "Branch", "type": "text"})
        notes.append("Combined ledger of all branches (no eliminations).")
    cols += [{"key": "jnl", "label": "Journal", "type": "text"},
             {"key": "descr", "label": "Description", "type": "text"},
             {"key": "ref", "label": "Ref", "type": "text"},
             {"key": "debit", "label": "Debit", "type": "money"},
             {"key": "credit", "label": "Credit", "type": "money"},
             {"key": "balance", "label": "Balance", "type": "money"}]
    return report(f"GL Ledger – {gl} {title}", codes, cols, rows,
                  f"{date_from.isoformat()} to {date_to.isoformat()}", notes)


# ---------------------------------------------------------------- dashboard helpers
def gl_kpis(codes: list[str], year: int, month: int) -> dict:
    L = Ledger(codes, year)
    bal = lambda g: g.balance(month)  # noqa: E731
    k = {"assets": 0.0, "deposits": 0.0, "profit": 0.0, "income": 0.0, "expenses": 0.0}
    for gl in L.gls:
        g, t = L.info(gl), L.amounts(gl, bal)["total"]
        if g.ctype == ASSET:
            k["assets"] += t
        if g.sort.startswith("401"):
            k["deposits"] -= t
        if g.ctype == INCOME:
            k["income"] -= t
        if g.ctype == EXPENSE:
            k["expenses"] += t
    k["profit"] = k["income"] - k["expenses"]
    return k


def monthly_trend(codes: list[str], year: int, last_month: int) -> list[dict]:
    L = Ledger(codes, year)
    out = []
    for m in range(1, last_month + 1):
        inc = exp = 0.0
        for gl in L.gls:
            g = L.info(gl)
            if g.ctype in (INCOME, EXPENSE):
                t = L.amounts(gl, lambda x: x.movement(m, m))["total"]
                if g.ctype == INCOME:
                    inc -= t
                else:
                    exp += t
        out.append({"month": MONTHS[m - 1], "income": inc, "expenses": exp, "profit": inc - exp})
    return out

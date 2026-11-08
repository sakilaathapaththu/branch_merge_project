from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.core.config import get_settings
from app.core.security import User, allowed_branch, current_user
from app.services import gl, portfolio
from app.services.export import to_xlsx
from app.services.report import money, resolve_branches

# Every report needs a logged-in user; branch users only see their own branch.
router = APIRouter(tags=["reports"], dependencies=[Depends(current_user)])

Branch = Query("all", description="'all' (consolidated) or a branch code, e.g. 001")
Format = Literal["json", "xlsx"]
Me = Depends(current_user)


def respond(rep: dict, format: Format):
    return to_xlsx(rep) if format == "xlsx" else rep


@router.get("/periods")
def periods():
    return gl.periods()


@router.get("/gl/accounts")
def gl_accounts():
    return gl.gl_accounts()


@router.get("/reports/trial-balance")
def trial_balance(branch: str = Branch, year: int | None = None, month: int | None = None,
                  show_zero: bool = False, format: Format = "json", user: User = Me):
    return respond(gl.trial_balance(allowed_branch(branch, user), year, month, show_zero), format)


@router.get("/reports/balance-sheet")
def balance_sheet(branch: str = Branch, year: int | None = None, month: int | None = None,
                  detail: bool = False, format: Format = "json", user: User = Me):
    return respond(gl.balance_sheet(allowed_branch(branch, user), year, month, detail), format)


@router.get("/reports/income-statement")
def income_statement(branch: str = Branch, year: int | None = None, from_month: int | None = None,
                     to_month: int | None = None, detail: bool = False, format: Format = "json",
                     user: User = Me):
    return respond(gl.income_statement(allowed_branch(branch, user), year, from_month, to_month, detail),
                   format)


@router.get("/reports/gl-ledger")
def gl_ledger(gl_code: str, date_from: date, date_to: date, branch: str = Branch,
              format: Format = "json", user: User = Me):
    return respond(gl.gl_ledger(allowed_branch(branch, user), gl_code, date_from, date_to), format)


@router.get("/reports/loan-portfolio")
def loan_portfolio(branch: str = Branch, format: Format = "json", user: User = Me):
    return respond(portfolio.loan_portfolio(allowed_branch(branch, user)), format)


@router.get("/reports/arrears-ageing")
def arrears_ageing(branch: str = Branch, format: Format = "json", user: User = Me):
    return respond(portfolio.arrears_ageing(allowed_branch(branch, user)), format)


@router.get("/reports/arrears-list")
def arrears_list(branch: str = Branch, min_days: int = Query(31, ge=1), format: Format = "json",
                 user: User = Me):
    return respond(portfolio.arrears_list(allowed_branch(branch, user), min_days), format)


@router.get("/reports/deposits")
def deposits(branch: str = Branch, format: Format = "json", user: User = Me):
    return respond(portfolio.deposits(allowed_branch(branch, user)), format)


@router.get("/reports/transactions")
def transactions(date_from: date, date_to: date, branch: str = Branch, acc: str | None = None,
                 format: Format = "json", user: User = Me):
    return respond(portfolio.transactions(allowed_branch(branch, user), date_from, date_to, acc or None),
                   format)


_MONEY_KPIS = ("assets", "deposits", "profit", "income", "expenses", "loans_outstanding",
               "par30_amount", "savings", "fixed_deposits")


@router.get("/dashboard")
def dashboard(user: User = Me):
    p = gl.periods()
    year, month = p["current_year"], p["last_month"]
    s = get_settings()
    codes = resolve_branches(allowed_branch("all", user))

    def kpis(cs: list[str]) -> dict:
        k = gl.gl_kpis(cs, year, month)
        port = [portfolio.portfolio_kpis(c) for c in cs]
        for key in ("loans_count", "loans_outstanding", "par30_amount", "savings",
                    "fixed_deposits", "deposit_accounts", "customers"):
            k[key] = sum(x[key] for x in port)
        k["par30_pct"] = k["par30_amount"] / k["loans_outstanding"] * 100 if k["loans_outstanding"] else 0
        k["as_of"] = max(x["as_of"] for x in port)
        for key in _MONEY_KPIS:
            k[key] = money(k[key])
        return k

    trend = [{**t, **{k: money(t[k]) for k in ("income", "expenses", "profit")}}
             for t in gl.monthly_trend(codes, year, month)]
    return {
        "year": year,
        "month": month,
        "branches": [{"code": c, "name": s.branches[c]["name"], "kpis": kpis([c])} for c in codes],
        "consolidated": kpis(codes) if len(codes) > 1 else None,
        "trend": trend,
    }

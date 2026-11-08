from datetime import date
from typing import Literal

from fastapi import APIRouter, Query

from app.core.config import get_settings
from app.services import gl, portfolio
from app.services.export import to_xlsx
from app.services.report import resolve_branches

router = APIRouter(tags=["reports"])

Branch = Query("all", description="'all' (consolidated) or a branch code, e.g. 001")
Format = Literal["json", "xlsx"]


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
                  show_zero: bool = False, format: Format = "json"):
    return respond(gl.trial_balance(branch, year, month, show_zero), format)


@router.get("/reports/balance-sheet")
def balance_sheet(branch: str = Branch, year: int | None = None, month: int | None = None,
                  detail: bool = False, format: Format = "json"):
    return respond(gl.balance_sheet(branch, year, month, detail), format)


@router.get("/reports/income-statement")
def income_statement(branch: str = Branch, year: int | None = None, from_month: int | None = None,
                     to_month: int | None = None, detail: bool = False, format: Format = "json"):
    return respond(gl.income_statement(branch, year, from_month, to_month, detail), format)


@router.get("/reports/gl-ledger")
def gl_ledger(gl_code: str, date_from: date, date_to: date, branch: str = Branch,
              format: Format = "json"):
    return respond(gl.gl_ledger(branch, gl_code, date_from, date_to), format)


@router.get("/reports/loan-portfolio")
def loan_portfolio(branch: str = Branch, format: Format = "json"):
    return respond(portfolio.loan_portfolio(branch), format)


@router.get("/reports/arrears-ageing")
def arrears_ageing(branch: str = Branch, format: Format = "json"):
    return respond(portfolio.arrears_ageing(branch), format)


@router.get("/reports/arrears-list")
def arrears_list(branch: str = Branch, min_days: int = Query(31, ge=1), format: Format = "json"):
    return respond(portfolio.arrears_list(branch, min_days), format)


@router.get("/reports/deposits")
def deposits(branch: str = Branch, format: Format = "json"):
    return respond(portfolio.deposits(branch), format)


@router.get("/reports/transactions")
def transactions(date_from: date, date_to: date, branch: str = Branch, acc: str | None = None,
                 format: Format = "json"):
    return respond(portfolio.transactions(branch, date_from, date_to, acc or None), format)


@router.get("/dashboard")
def dashboard():
    p = gl.periods()
    year, month = p["current_year"], p["last_month"]
    s = get_settings()
    codes = resolve_branches("all")

    def kpis(cs: list[str]) -> dict:
        k = gl.gl_kpis(cs, year, month)
        port = [portfolio.portfolio_kpis(c) for c in cs]
        for key in ("loans_count", "loans_outstanding", "par30_amount", "savings",
                    "fixed_deposits", "deposit_accounts", "customers"):
            k[key] = sum(x[key] for x in port)
        k["par30_pct"] = k["par30_amount"] / k["loans_outstanding"] * 100 if k["loans_outstanding"] else 0
        k["as_of"] = max(x["as_of"] for x in port)
        return k

    return {
        "year": year,
        "month": month,
        "branches": [{"code": c, "name": s.branches[c]["name"], "kpis": kpis([c])} for c in codes],
        "consolidated": kpis(codes),
        "trend": gl.monthly_trend(codes, year, month),
    }

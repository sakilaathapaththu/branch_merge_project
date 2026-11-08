from datetime import date
from io import BytesIO
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook

from app.core.security import User, allowed_branch, current_user
from app.services import reports as svc

Branch = Literal["001", "002", "all"]

router = APIRouter(tags=["reports"])

Me = Depends(current_user)


@router.get("/gl/accounts")
def gl_accounts(branch: Branch = "all", user: User = Me):
    return svc.gl_accounts(allowed_branch(branch, user))


@router.get("/reports/trial-balance")
def trial_balance(date: date = Query(...), branch: Branch = "all", user: User = Me):
    return svc.trial_balance(date, allowed_branch(branch, user))


@router.get("/reports/balance-sheet")
def balance_sheet(date: date = Query(...), branch: Branch = "all", user: User = Me):
    return svc.balance_sheet(date, allowed_branch(branch, user))


@router.get("/reports/profit-loss")
def profit_loss(
    date_from: date = Query(..., alias="from"),
    date_to: date = Query(..., alias="to"),
    branch: Branch = "all",
    user: User = Me,
):
    branch = allowed_branch(branch, user)
    if date_from > date_to:
        raise HTTPException(400, "'from' must be on or before 'to'")
    return svc.profit_loss(date_from, date_to, branch)


@router.get("/transactions")
def transactions(
    branch: Branch = "all",
    user: User = Me,
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    acc: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
):
    branch = allowed_branch(branch, user)
    return svc.transactions(branch, date_from, date_to, acc, page, size)


def _sheet_rows(name: str, data: dict) -> tuple[list[str], list[list]]:
    if name == "trial-balance":
        return (["GL Account", "Code", "Title", "Type", "Debit", "Credit"],
                [[l["glAcc"], l["code"], l["title"], l["type"], l["debit"], l["credit"]]
                 for l in data["lines"]]
                + [["", "", "TOTAL", "", data["totalDebit"], data["totalCredit"]]])
    sections = (
        [("Assets", "assets"), ("Liabilities", "liabilities"), ("Equity", "equity")]
        if name == "balance-sheet"
        else [("Income", "income"), ("Expenses", "expenses")]
    )
    rows: list[list] = []
    for label, key in sections:
        rows.append([label.upper(), "", ""])
        for g in data[key]:
            rows.append([g["sortCode"], g["title"], g["amount"]])
            rows += [[a["code"], "   " + a["title"], a["amount"]] for a in g["accounts"]]
    if name == "balance-sheet":
        rows += [["", "Current year profit", data["currentYearProfit"]],
                 ["", "Total assets", data["totalAssets"]],
                 ["", "Total liabilities + equity", data["totalLiabilitiesAndEquity"]]]
    else:
        rows += [["", "Total income", data["totalIncome"]],
                 ["", "Total expenses", data["totalExpenses"]],
                 ["", "Net profit", data["netProfit"]]]
    return ["Code", "Title", "Amount"], rows


@router.get("/reports/{name}/export")
def export(
    name: Literal["trial-balance", "balance-sheet", "profit-loss"],
    format: Literal["xlsx"] = "xlsx",
    branch: Branch = "all",
    user: User = Me,
    date: date | None = None,
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
):
    branch = allowed_branch(branch, user)
    if name == "profit-loss":
        if not (date_from and date_to):
            raise HTTPException(400, "'from' and 'to' are required")
        data = svc.profit_loss(date_from, date_to, branch)
    else:
        if not date:
            raise HTTPException(400, "'date' is required")
        data = (svc.trial_balance if name == "trial-balance" else svc.balance_sheet)(date, branch)

    header, rows = _sheet_rows(name, data)
    wb = Workbook()
    ws = wb.active
    ws.title = name
    ws.append([f"{name.replace('-', ' ').title()} – branch {branch}"])
    ws.append([f"{k}: {data[k]}" for k in ("asOf", "from", "to") if k in data])
    ws.append(header)
    for r in rows:
        ws.append(r)
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{name}-{branch}.xlsx"'},
    )

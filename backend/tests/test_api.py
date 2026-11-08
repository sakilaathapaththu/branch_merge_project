"""Integration tests: need SQL Server with the branch databases from .env."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def get(path: str, **params):
    r = client.get(path, params=params)
    assert r.status_code == 200, r.text
    return r.json()


def total_row(rep):
    return next(r for r in rep["rows"] if r.get("_style") == "total")


def test_branches():
    assert [b["code"] for b in get("/api/branches")] == ["001", "002"]


def test_health():
    assert get("/api/health")["status"] == "ok"


@pytest.mark.parametrize("branch", ["001", "002", "all"])
def test_trial_balance_balances(branch):
    t = total_row(get("/api/reports/trial-balance", branch=branch))
    assert abs(t["debit"] - t["credit"]) < 1


def test_consolidated_tb_equals_sum_of_branches():
    ho = total_row(get("/api/reports/trial-balance", branch="001"))
    br = total_row(get("/api/reports/trial-balance", branch="002"))
    al = get("/api/reports/trial-balance", branch="all")
    # Without eliminations the consolidated net per GL is HO + BR.
    for row in al["rows"][:-1]:
        assert abs(row["b001"] + row["b002"] + row["elim"] - (row["debit"] - row["credit"])) < 1
    assert ho["debit"] > 0 and br["debit"] > 0


def test_inter_branch_eliminated():
    rows = {r["gl"]: r for r in get("/api/reports/trial-balance", branch="all")["rows"]}
    for gl in ("418010101", "315400101"):
        assert abs(rows[gl]["debit"]) < 1 and abs(rows[gl]["credit"]) < 1


@pytest.mark.parametrize("branch", ["001", "002", "all"])
def test_balance_sheet_balances(branch):
    rep = get("/api/reports/balance-sheet", branch=branch)
    rows = {r["label"]: r for r in rep["rows"]}
    assert abs(rows["TOTAL ASSETS"]["total"] - rows["TOTAL LIABILITIES & EQUITY"]["total"]) < 1


def test_profit_matches_between_reports():
    bs = {r["label"]: r for r in get("/api/reports/balance-sheet", branch="all")["rows"]}
    pl = {r["label"]: r for r in get("/api/reports/income-statement", branch="all")["rows"]}
    assert abs(bs["Current year profit / (loss)"]["total"] - pl["NET PROFIT / (LOSS)"]["total"]) < 1


def test_gl_ledger_reconciles_to_trial_balance():
    p = get("/api/periods")
    gl = "105010103"
    led = get("/api/reports/gl-ledger", gl_code=gl, branch="001",
              date_from=f"{p['current_year']}-01-01", date_to=f"{p['current_year']}-12-31")
    tb = {r["gl"]: r for r in get("/api/reports/trial-balance", branch="001", month=12)["rows"]}
    assert abs(total_row(led)["balance"] - (tb[gl]["debit"] - tb[gl]["credit"])) < 1


@pytest.mark.parametrize("path", ["loan-portfolio", "arrears-ageing", "arrears-list", "deposits"])
def test_portfolio_reports(path):
    rep = get(f"/api/reports/{path}", branch="all")
    assert rep["columns"] and rep["rows"]


def test_arrears_ageing_matches_portfolio():
    lp = total_row(get("/api/reports/loan-portfolio", branch="all"))
    ag = total_row(get("/api/reports/arrears-ageing", branch="all"))
    assert abs(lp["outstanding"] - ag["outstanding"]) < 1


def test_transactions_range_limit():
    r = client.get("/api/reports/transactions", params={"date_from": "2026-01-01", "date_to": "2026-06-01"})
    assert r.status_code == 400


def test_excel_export():
    r = client.get("/api/reports/trial-balance", params={"branch": "all", "format": "xlsx"})
    assert r.status_code == 200
    assert r.content[:2] == b"PK"


def test_dashboard():
    d = get("/api/dashboard")
    c = d["consolidated"]
    assert c["assets"] > 0 and c["loans_outstanding"] > 0 and len(d["branches"]) == 2


def test_bad_branch():
    assert client.get("/api/reports/trial-balance", params={"branch": "999"}).status_code == 400

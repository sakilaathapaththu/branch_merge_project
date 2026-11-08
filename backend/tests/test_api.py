"""Integration tests: need SQL Server with the branch databases from .env
(and MB_Consolidated.dbo.AppUsers for the login tests)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import get_engine
from app.core.security import User, create_token, hash_password, verify_password
from app.main import app

client = TestClient(app)


def auth(role: str = "admin", branch: str = "all") -> dict:
    return {"Authorization": f"Bearer {create_token(User(f't_{role}_{branch}', 'Test', role, branch))}"}


ADMIN = auth()


def get(path: str, headers: dict = ADMIN, **params):
    r = client.get(path, params=params, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def total_row(rep):
    return next(r for r in rep["rows"] if r.get("_style") == "total")


# ---------------------------------------------------------------- auth
def test_password_hash_roundtrip():
    h = hash_password("s3cret-pass")
    assert verify_password("s3cret-pass", h) and not verify_password("wrong", h)


def test_reports_require_login():
    assert client.get("/api/branches").status_code == 401
    assert client.get("/api/reports/trial-balance").status_code == 401
    assert client.get("/api/dashboard").status_code == 401
    assert client.get("/api/branches", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_viewer_cannot_manage_users():
    assert client.get("/api/auth/users", headers=auth("viewer")).status_code == 403


def test_branch_user_blocked_from_other_branch():
    r = client.get("/api/reports/trial-balance", params={"branch": "001"}, headers=auth("viewer", "002"))
    assert r.status_code == 403


def test_branch_user_sees_only_own_branch():
    assert [b["code"] for b in get("/api/branches", auth("viewer", "002"))] == ["002"]
    rep = get("/api/reports/trial-balance", auth("viewer", "002"), branch="all")
    assert rep["subtitle"].startswith("002")
    d = get("/api/dashboard", auth("viewer", "002"))
    assert [b["code"] for b in d["branches"]] == ["002"] and d["consolidated"] is None


@pytest.fixture
def temp_user():
    name, t = "pytest_tmp_user", f"[{get_settings().db_consolidated}].dbo.AppUsers"
    with get_engine().begin() as c:
        c.execute(text(f"DELETE FROM {t} WHERE Username = :u"), {"u": name})
    yield name
    with get_engine().begin() as c:
        c.execute(text(f"DELETE FROM {t} WHERE Username = :u"), {"u": name})


def test_user_create_login_disable(temp_user):
    body = {"username": temp_user, "fullName": "Py Test", "password": "Passw0rd!x",
            "role": "viewer", "branch": "001"}
    assert client.post("/api/auth/users", json=body, headers=ADMIN).status_code == 201
    assert client.post("/api/auth/users", json=body, headers=ADMIN).status_code == 409
    creds = {"username": temp_user, "password": "Passw0rd!x"}
    r = client.post("/api/auth/login", json=creds)
    assert r.status_code == 200
    me = get("/api/auth/me", {"Authorization": f"Bearer {r.json()['token']}"})
    assert me["branch"] == "001" and me["role"] == "viewer"
    assert client.post("/api/auth/login", json={**creds, "password": "nope"}).status_code == 401
    client.patch(f"/api/auth/users/{temp_user}", json={"active": False}, headers=ADMIN)
    assert client.post("/api/auth/login", json=creds).status_code == 401


# ---------------------------------------------------------------- reports
def test_branches():
    assert [b["code"] for b in get("/api/branches")] == ["001", "002"]


def test_health():
    assert client.get("/api/health").json()["status"] == "ok"


@pytest.mark.parametrize("branch", ["001", "002", "all"])
def test_trial_balance_balances(branch):
    t = total_row(get("/api/reports/trial-balance", branch=branch))
    assert abs(t["debit"] - t["credit"]) < 0.01


def test_consolidated_tb_equals_sum_of_branches():
    ho = total_row(get("/api/reports/trial-balance", branch="001"))
    br = total_row(get("/api/reports/trial-balance", branch="002"))
    al = get("/api/reports/trial-balance", branch="all")
    for row in al["rows"][:-1]:
        assert abs(row["b001"] + row["b002"] + row["elim"] - (row["debit"] - row["credit"])) < 0.01
    assert ho["debit"] > 0 and br["debit"] > 0


def test_money_in_rupees():
    # HO chief cashier cash is 53,103,616 cents in MBWin = LKR 531,036.16
    rows = {r["gl"]: r for r in get("/api/reports/trial-balance", branch="001", month=10)["rows"]}
    assert abs(rows["311010101"]["debit"] - 531036.16) < 0.01


def test_inter_branch_eliminated():
    rows = {r["gl"]: r for r in get("/api/reports/trial-balance", branch="all")["rows"]}
    for gl in ("418010101", "315400101"):
        assert abs(rows[gl]["debit"]) < 0.01 and abs(rows[gl]["credit"]) < 0.01


@pytest.mark.parametrize("branch", ["001", "002", "all"])
def test_balance_sheet_balances(branch):
    rows = {r["label"]: r for r in get("/api/reports/balance-sheet", branch=branch)["rows"]}
    assert abs(rows["TOTAL ASSETS"]["total"] - rows["TOTAL LIABILITIES & EQUITY"]["total"]) < 0.01


def test_profit_matches_between_reports():
    bs = {r["label"]: r for r in get("/api/reports/balance-sheet", branch="all")["rows"]}
    pl = {r["label"]: r for r in get("/api/reports/income-statement", branch="all")["rows"]}
    assert abs(bs["Current year profit / (loss)"]["total"] - pl["NET PROFIT / (LOSS)"]["total"]) < 0.01


def test_gl_ledger_reconciles_to_trial_balance():
    p = get("/api/periods")
    gl = "105010103"
    led = get("/api/reports/gl-ledger", gl_code=gl, branch="001",
              date_from=f"{p['current_year']}-01-01", date_to=f"{p['current_year']}-12-31")
    tb = {r["gl"]: r for r in get("/api/reports/trial-balance", branch="001", month=12)["rows"]}
    assert abs(total_row(led)["balance"] - (tb[gl]["debit"] - tb[gl]["credit"])) < 0.01


@pytest.mark.parametrize("path", ["loan-portfolio", "arrears-ageing", "arrears-list", "deposits"])
def test_portfolio_reports(path):
    rep = get(f"/api/reports/{path}", branch="all")
    assert rep["columns"] and rep["rows"]


def test_arrears_ageing_matches_portfolio():
    lp = total_row(get("/api/reports/loan-portfolio", branch="all"))
    ag = total_row(get("/api/reports/arrears-ageing", branch="all"))
    assert abs(lp["outstanding"] - ag["outstanding"]) < 0.01


def test_transactions_range_limit():
    r = client.get("/api/reports/transactions", headers=ADMIN,
                   params={"date_from": "2026-01-01", "date_to": "2026-06-01"})
    assert r.status_code == 400


def test_excel_export():
    r = client.get("/api/reports/trial-balance", headers=ADMIN, params={"branch": "all", "format": "xlsx"})
    assert r.status_code == 200 and r.content[:2] == b"PK"


def test_dashboard():
    d = get("/api/dashboard")
    c = d["consolidated"]
    assert c["assets"] > 0 and c["loans_outstanding"] > 0 and len(d["branches"]) == 2


def test_bad_branch():
    r = client.get("/api/reports/trial-balance", params={"branch": "999"}, headers=ADMIN)
    assert r.status_code == 400

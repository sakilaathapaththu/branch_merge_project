import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import get_engine
from app.core.security import User, create_token, hash_password, verify_password
from app.main import app

client = TestClient(app)
DATE = "2026-10-31"


def auth(role: str = "admin", branch: str = "all") -> dict:
    token = create_token(User(f"t_{role}_{branch}", "Test", role, branch))
    return {"Authorization": f"Bearer {token}"}


ADMIN = auth()


def _db_ready() -> bool:
    return client.get("/api/health").json()["status"] == "ok"


needs_db = pytest.mark.skipif(not _db_ready(), reason="SQL Server databases not available")


# ---------- auth basics (no DB) ----------

def test_password_hash_roundtrip():
    h = hash_password("s3cret-pass")
    assert verify_password("s3cret-pass", h)
    assert not verify_password("wrong", h)


def test_reports_require_login():
    assert client.get("/api/branches").status_code == 401
    assert client.get(f"/api/reports/trial-balance?date={DATE}").status_code == 401
    bad = {"Authorization": "Bearer not-a-token"}
    assert client.get("/api/branches", headers=bad).status_code == 401


def test_branches():
    r = client.get("/api/branches", headers=ADMIN)
    assert [b["code"] for b in r.json()] == ["001", "002"]
    r = client.get("/api/branches", headers=auth("viewer", "002"))
    assert [b["code"] for b in r.json()] == ["002"]


def test_viewer_cannot_manage_users():
    assert client.get("/api/auth/users", headers=auth("viewer")).status_code == 403


def test_health_responds():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] in {"ok", "degraded", "error"}


def test_invalid_branch_rejected():
    r = client.get(f"/api/reports/trial-balance?date={DATE}&branch=999", headers=ADMIN)
    assert r.status_code == 422


def test_branch_user_blocked_from_other_branch():
    r = client.get(f"/api/reports/trial-balance?date={DATE}&branch=001", headers=auth("viewer", "002"))
    assert r.status_code == 403


# ---------- reports (need DB) ----------

@needs_db
@pytest.mark.parametrize("branch", ["001", "002", "all"])
def test_trial_balance_balances(branch):
    tb = client.get(f"/api/reports/trial-balance?date={DATE}&branch={branch}", headers=ADMIN).json()
    assert tb["balanced"] and tb["totalDebit"] == tb["totalCredit"]


@needs_db
def test_consolidated_equals_sum_of_branches():
    bs = {b: client.get(f"/api/reports/balance-sheet?date={DATE}&branch={b}", headers=ADMIN).json()
          for b in ("001", "002", "all")}
    assert all(r["balanced"] for r in bs.values())
    assert round(bs["001"]["totalAssets"] + bs["002"]["totalAssets"], 2) == bs["all"]["totalAssets"]


@needs_db
def test_profit_loss_matches_balance_sheet():
    pl = client.get(f"/api/reports/profit-loss?from=2026-01-01&to={DATE}", headers=ADMIN).json()
    bs = client.get(f"/api/reports/balance-sheet?date={DATE}", headers=ADMIN).json()
    assert pl["netProfit"] == bs["currentYearProfit"]


@needs_db
def test_branch_user_all_is_narrowed():
    r = client.get(f"/api/reports/trial-balance?date={DATE}&branch=all", headers=auth("viewer", "002"))
    assert r.status_code == 200 and r.json()["branch"] == "002"


# ---------- login + user management (needs DB, uses a temp user) ----------

@pytest.fixture
def temp_user():
    name = "pytest_tmp_user"
    t = f"[{get_settings().db_consolidated}].dbo.AppUsers"
    with get_engine().begin() as c:
        c.execute(text(f"DELETE FROM {t} WHERE Username = :u"), {"u": name})
    yield name
    with get_engine().begin() as c:
        c.execute(text(f"DELETE FROM {t} WHERE Username = :u"), {"u": name})


@needs_db
def test_user_create_login_disable(temp_user):
    body = {"username": temp_user, "fullName": "Py Test", "password": "Passw0rd!x",
            "role": "viewer", "branch": "001"}
    assert client.post("/api/auth/users", json=body, headers=ADMIN).status_code == 201
    assert client.post("/api/auth/users", json=body, headers=ADMIN).status_code == 409

    r = client.post("/api/auth/login", json={"username": temp_user, "password": "Passw0rd!x"})
    assert r.status_code == 200
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {r.json()['token']}"}).json()
    assert me["branch"] == "001" and me["role"] == "viewer"

    assert client.post("/api/auth/login", json={"username": temp_user, "password": "nope"}).status_code == 401
    client.patch(f"/api/auth/users/{temp_user}", json={"active": False}, headers=ADMIN)
    assert client.post("/api/auth/login", json={"username": temp_user, "password": "Passw0rd!x"}).status_code == 401

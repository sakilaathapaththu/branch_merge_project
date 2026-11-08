from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_branches():
    r = client.get("/api/branches")
    assert r.status_code == 200
    assert [b["code"] for b in r.json()] == ["001", "002"]


def test_health_responds():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] in {"ok", "degraded", "error"}


# The tests below need the restored MBWin databases and MB_Consolidated views.
import pytest

DATE = "2026-10-31"


def _db_ready() -> bool:
    return client.get("/api/health").json()["status"] == "ok"


needs_db = pytest.mark.skipif(not _db_ready(), reason="SQL Server databases not available")


@needs_db
@pytest.mark.parametrize("branch", ["001", "002", "all"])
def test_trial_balance_balances(branch):
    tb = client.get(f"/api/reports/trial-balance?date={DATE}&branch={branch}").json()
    assert tb["balanced"] and tb["totalDebit"] == tb["totalCredit"]


@needs_db
def test_consolidated_equals_sum_of_branches():
    bs = {b: client.get(f"/api/reports/balance-sheet?date={DATE}&branch={b}").json()
          for b in ("001", "002", "all")}
    assert all(r["balanced"] for r in bs.values())
    assert round(bs["001"]["totalAssets"] + bs["002"]["totalAssets"], 2) == bs["all"]["totalAssets"]


@needs_db
def test_profit_loss_matches_balance_sheet():
    pl = client.get(f"/api/reports/profit-loss?from=2026-01-01&to={DATE}").json()
    bs = client.get(f"/api/reports/balance-sheet?date={DATE}").json()
    assert pl["netProfit"] == bs["currentYearProfit"]


def test_invalid_branch_rejected():
    assert client.get(f"/api/reports/trial-balance?date={DATE}&branch=999").status_code == 422

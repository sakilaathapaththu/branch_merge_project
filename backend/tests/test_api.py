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

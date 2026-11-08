from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import get_engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """API status plus whether each branch database is reachable."""
    s = get_settings()
    databases: dict[str, str] = {}
    try:
        with get_engine().connect() as conn:
            for code, b in s.branches.items():
                state = conn.execute(
                    text("SELECT state_desc FROM sys.databases WHERE name = :n"),
                    {"n": b["database"]},
                ).scalar()
                databases[code] = state or "NOT FOUND"
        status = "ok" if all(v == "ONLINE" for v in databases.values()) else "degraded"
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": str(exc).splitlines()[0]}
    return {"status": status, "databases": databases}

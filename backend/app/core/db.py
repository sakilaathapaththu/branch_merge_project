import time
from decimal import Decimal
from functools import lru_cache
from typing import Any
from urllib.parse import quote_plus

from sqlalchemy import Engine, create_engine, text

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    """Engine on master; queries use fully qualified [db].dbo.[table] names.

    The backend only ever reads. Production should use a SQL login that has
    db_datareader only on the MBWin databases.
    """
    s = get_settings()
    auth = (
        f"UID={s.db_user};PWD={s.db_password};"
        if s.db_user
        else "Trusted_Connection=yes;"
    )
    odbc = (
        f"DRIVER={{{s.db_driver}}};SERVER={s.db_server};DATABASE=master;"
        f"{auth}ApplicationIntent=ReadOnly;"
    )
    return create_engine(
        f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc)}",
        pool_pre_ping=True,
    )


def _clean(v: Any) -> Any:
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, str):
        return v.strip()
    return v


def query(sql: str, params: dict | None = None) -> list[dict]:
    with get_engine().connect() as conn:
        res = conn.execute(text(sql), params or {})
        cols = list(res.keys())
        return [{c: _clean(v) for c, v in zip(cols, row)} for row in res]


_cache: dict[tuple, tuple[float, Any]] = {}


def cached_query(sql: str, params: dict | None = None, ttl: int = 120) -> list[dict]:
    """Short TTL cache: one page load reads the same GL tables several times."""
    key = (sql, tuple(sorted((params or {}).items())))
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < ttl:
        return hit[1]
    rows = query(sql, params)
    _cache[key] = (time.monotonic(), rows)
    return rows

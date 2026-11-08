from functools import lru_cache
from urllib.parse import quote_plus

from sqlalchemy import Engine, create_engine

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

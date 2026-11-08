from functools import lru_cache
from urllib.parse import quote_plus

from sqlalchemy import Engine, create_engine

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    """Engine on master; queries use fully qualified [db].dbo.[table] names.

    MBWin data is only ever read. The one write target is
    MB_Consolidated.dbo.AppUsers (login users). Production uses the
    branchmerge_ro login: db_datareader + write on AppUsers only.
    """
    s = get_settings()
    auth = (
        f"UID={s.db_user};PWD={s.db_password};"
        if s.db_user
        else "Trusted_Connection=yes;"
    )
    odbc = (
        f"DRIVER={{{s.db_driver}}};SERVER={s.db_server};DATABASE=master;"
        f"{auth}"
    )
    return create_engine(
        f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc)}",
        pool_pre_ping=True,
    )

import re
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

_DB_NAME = re.compile(r"^[A-Za-z0-9_]+$")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_server: str = r"SAKILA\SQLEXPRESS"
    db_driver: str = "ODBC Driver 17 for SQL Server"
    db_user: str = ""
    db_password: str = ""

    db_ho: str = "MicroBanker_ho_BeforeEOM_20261031"
    db_br: str = "MicroBanker_br_EOM_20261031"

    cors_origins: str = "http://localhost:3000"

    # Inter-branch GL accounts eliminated in consolidated figures, as
    # "branch:gl" pairs; groups separated by ";". Each group must net to zero.
    #   HO 418010101 Branch Advances - Mahapitiya  <->  BR 315400101 Branch Advances - Ahugoda
    #   HO 201040102 Branch Advance interest       <->  BR 120010117 Branch Advance Interest Income
    eliminations: str = "001:418010101,002:315400101;001:201040102,002:120010117"

    @property
    def branches(self) -> dict[str, dict[str, str]]:
        """Branch code -> name and source database. Database names are
        validated because they are interpolated into SQL as identifiers."""
        out = {
            "001": {"name": "Head Office", "short": "HO", "database": self.db_ho},
            "002": {"name": "Mahapitiya Branch", "short": "Mahapitiya", "database": self.db_br},
        }
        for b in out.values():
            if not _DB_NAME.match(b["database"]):
                raise ValueError(f"Invalid database name: {b['database']!r}")
        return out

    @property
    def elimination_groups(self) -> list[list[tuple[str, str]]]:
        groups = []
        for grp in filter(None, self.eliminations.split(";")):
            pairs = [p.strip().split(":", 1) for p in grp.split(",") if p.strip()]
            groups.append([(b, gl) for b, gl in pairs])
        return groups


@lru_cache
def get_settings() -> Settings:
    return Settings()

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_server: str = r"SAKILA\SQLEXPRESS"
    db_driver: str = "ODBC Driver 17 for SQL Server"
    db_user: str = ""
    db_password: str = ""

    db_ho: str = "MicroBanker_ho_BeforeEOM_20261031"
    db_br: str = "MicroBanker_br_EOM_20261031"
    db_consolidated: str = "MB_Consolidated"

    cors_origins: str = "http://localhost:3000"

    @property
    def branches(self) -> dict[str, dict[str, str]]:
        """Branch code -> name and source database."""
        return {
            "001": {"name": "Head Office", "database": self.db_ho},
            "002": {"name": "Mahapitiya Branch", "database": self.db_br},
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()

"""AppUsers table in MB_Consolidated – the only table the backend writes to."""
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import get_engine
from app.core.security import User, hash_password, verify_password

_COLS = "Username, FullName, Role, Branch, Active, CreatedAt, LastLoginAt"


def _t() -> str:
    return f"[{get_settings().db_consolidated}].dbo.AppUsers"


def _public(r) -> dict:
    return {
        "username": r.Username,
        "fullName": r.FullName,
        "role": r.Role,
        "branch": r.Branch,
        "active": bool(r.Active),
        "createdAt": r.CreatedAt.isoformat() if r.CreatedAt else None,
        "lastLoginAt": r.LastLoginAt.isoformat() if r.LastLoginAt else None,
    }


def authenticate(username: str, password: str) -> User | None:
    with get_engine().begin() as conn:
        r = conn.execute(
            text(f"SELECT {_COLS}, PasswordHash FROM {_t()} WHERE Username = :u"),
            {"u": username},
        ).first()
        if not r or not r.Active or not verify_password(password, r.PasswordHash):
            return None
        conn.execute(text(f"UPDATE {_t()} SET LastLoginAt = SYSDATETIME() WHERE Username = :u"),
                     {"u": username})
        return User(r.Username, r.FullName, r.Role, r.Branch)


def list_users() -> list[dict]:
    with get_engine().connect() as conn:
        return [_public(r) for r in conn.execute(text(f"SELECT {_COLS} FROM {_t()} ORDER BY Username"))]


def get_user(username: str) -> dict | None:
    with get_engine().connect() as conn:
        r = conn.execute(text(f"SELECT {_COLS} FROM {_t()} WHERE Username = :u"), {"u": username}).first()
        return _public(r) if r else None


def create_user(username: str, full_name: str, password: str, role: str, branch: str) -> dict:
    with get_engine().begin() as conn:
        conn.execute(
            text(f"INSERT INTO {_t()} (Username, FullName, PasswordHash, Role, Branch) "
                 f"VALUES (:u, :n, :p, :r, :b)"),
            {"u": username, "n": full_name, "p": hash_password(password), "r": role, "b": branch},
        )
    return get_user(username)


def update_user(username: str, *, full_name=None, password=None, role=None, branch=None, active=None) -> dict | None:
    sets, params = [], {"u": username}
    for col, key, val in (("FullName", "n", full_name), ("Role", "r", role),
                          ("Branch", "b", branch), ("Active", "a", active)):
        if val is not None:
            sets.append(f"{col} = :{key}")
            params[key] = val
    if password is not None:
        sets.append("PasswordHash = :p")
        params["p"] = hash_password(password)
    if sets:
        with get_engine().begin() as conn:
            conn.execute(text(f"UPDATE {_t()} SET {', '.join(sets)} WHERE Username = :u"), params)
    return get_user(username)


def count_active_admins() -> int:
    with get_engine().connect() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM {_t()} WHERE Role = 'admin' AND Active = 1")).scalar()

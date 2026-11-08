"""Password hashing, JWT tokens and the current-user dependencies."""
import base64
import hashlib
import hmac
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

_ITERATIONS = 600_000
_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    b64 = lambda b: base64.b64encode(b).decode()  # noqa: E731
    return f"pbkdf2_sha256${_ITERATIONS}${b64(salt)}${b64(dk)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt, dk = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        calc = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt), int(iters))
        return hmac.compare_digest(calc, base64.b64decode(dk))
    except (ValueError, TypeError):
        return False


def _secret() -> str:
    s = get_settings().jwt_secret
    if len(s) < 32:
        raise HTTPException(500, "JWT_SECRET is not configured (min 32 characters)")
    return s


@dataclass
class User:
    username: str
    full_name: str
    role: str  # admin | viewer
    branch: str  # all | 001 | 002

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def create_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.username,
        "name": user.full_name,
        "role": user.role,
        "branch": user.branch,
        "iat": now,
        "exp": now + timedelta(minutes=get_settings().jwt_expire_minutes),
    }
    return jwt.encode(payload, _secret(), algorithm="HS256")


def current_user(cred: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> User:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        p = jwt.decode(cred.credentials, _secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token",
                            headers={"WWW-Authenticate": "Bearer"})
    return User(p["sub"], p.get("name", p["sub"]), p["role"], p["branch"])


def admin_user(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    return user


def allowed_branch(requested: str, user: User) -> str:
    """Users tied to one branch only see that branch; 'all' is narrowed for them."""
    if user.branch == "all":
        return requested
    if requested in ("all", user.branch):
        return user.branch
    raise HTTPException(status.HTTP_403_FORBIDDEN, f"No access to branch {requested}")

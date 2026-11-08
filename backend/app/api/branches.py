from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.core.security import User, current_user

router = APIRouter(prefix="/branches", tags=["branches"])


@router.get("")
def list_branches(user: User = Depends(current_user)) -> list[dict]:
    return [
        {"code": code, "name": b["name"]}
        for code, b in get_settings().branches.items()
        if user.branch in ("all", code)
    ]

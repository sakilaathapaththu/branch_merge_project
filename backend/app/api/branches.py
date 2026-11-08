from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/branches", tags=["branches"])


@router.get("")
def list_branches() -> list[dict]:
    return [
        {"code": code, "name": b["name"]}
        for code, b in get_settings().branches.items()
    ]

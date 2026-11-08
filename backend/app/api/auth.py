from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from app.core.security import User, admin_user, create_token, current_user
from app.services import users as svc

router = APIRouter(prefix="/auth", tags=["auth"])

Role = Literal["admin", "viewer"]
UserBranch = Literal["all", "001", "002"]


class LoginIn(BaseModel):
    username: str
    password: str


class UserIn(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9._-]+$")
    fullName: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    role: Role = "viewer"
    branch: UserBranch = "all"


class UserPatch(BaseModel):
    fullName: str | None = Field(None, min_length=1, max_length=100)
    password: str | None = Field(None, min_length=8, max_length=128)
    role: Role | None = None
    branch: UserBranch | None = None
    active: bool | None = None


def _me(u: User) -> dict:
    return {"username": u.username, "fullName": u.full_name, "role": u.role, "branch": u.branch}


@router.post("/login")
def login(body: LoginIn):
    user = svc.authenticate(body.username.strip(), body.password)
    if not user:
        raise HTTPException(401, "Invalid username or password")
    return {"token": create_token(user), "user": _me(user)}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return _me(user)


@router.get("/users")
def list_users(_: User = Depends(admin_user)):
    return svc.list_users()


@router.post("/users", status_code=201)
def create_user(body: UserIn, _: User = Depends(admin_user)):
    try:
        return svc.create_user(body.username, body.fullName, body.password, body.role, body.branch)
    except IntegrityError:
        raise HTTPException(409, f"User '{body.username}' already exists")


@router.patch("/users/{username}")
def update_user(username: str, body: UserPatch, me_: User = Depends(admin_user)):
    existing = svc.get_user(username)
    if not existing:
        raise HTTPException(404, "User not found")
    demoting = existing["role"] == "admin" and existing["active"] and (
        body.role == "viewer" or body.active is False
    )
    if demoting and svc.count_active_admins() <= 1:
        raise HTTPException(400, "Cannot remove the last active admin")
    return svc.update_user(username, full_name=body.fullName, password=body.password,
                           role=body.role, branch=body.branch, active=body.active)

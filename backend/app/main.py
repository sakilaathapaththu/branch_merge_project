from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, branches, health, reports
from app.core.config import get_settings

app = FastAPI(
    title="Branch Merge API",
    description="Read-only consolidated reporting over MicroBanker branch databases",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",")],
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(branches.router, prefix="/api")
app.include_router(reports.router, prefix="/api")

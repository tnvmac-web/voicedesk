"""VoiceDesk FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import get_settings
from app.init_db import create_tables
from app.routers import (
    agent,
    analytics,
    appointments,
    auth,
    calls,
    contacts,
    health,
    inbox,
    telephony,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    create_tables()
    yield


app = FastAPI(
    title=f"{settings.app_name} API",
    version=__version__,
    description="Self-hosted AI voice + WhatsApp/SMS receptionist.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_dev else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (
    health.router,
    auth.router,
    agent.router,
    contacts.router,
    appointments.router,
    calls.router,
    inbox.router,
    telephony.router,
    analytics.router,
):
    app.include_router(r)


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
    }

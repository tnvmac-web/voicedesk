"""Health & meta endpoints (no auth)."""

from __future__ import annotations

from fastapi import APIRouter

from app import __version__
from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    s = get_settings()
    return {
        "status": "ok",
        "app": s.app_name,
        "version": __version__,
        "env": s.env,
        "telephony": s.telephony_provider,
        "stt": s.stt_provider,
        "llm": s.llm_provider,
        "tts": s.tts_provider,
    }

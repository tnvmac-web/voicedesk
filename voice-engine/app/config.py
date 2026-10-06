"""Application configuration (pydantic-settings).

Every provider defaults to `mock` so the app boots and is fully testable
with zero API keys. Real providers activate by setting env vars.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- App ---
    app_name: str = "VoiceDesk"
    env: Literal["dev", "test", "prod"] = "dev"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 720
    public_base_url: str = "http://127.0.0.1:8000"

    # --- Database ---
    database_url: str = "sqlite:///./voicedesk.db"

    # --- Telephony ---
    telephony_provider: Literal["twilio", "vonage", "telnyx", "mock"] = "mock"
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    vonage_api_key: str = ""
    vonage_api_secret: str = ""
    vonage_application_id: str = ""
    telnyx_api_key: str = ""
    telnyx_connection_id: str = ""

    # --- STT ---
    stt_provider: Literal["deepgram", "whisper", "mock"] = "mock"
    deepgram_api_key: str = ""

    # --- LLM ---
    llm_provider: Literal["openai", "anthropic", "ollama", "mock"] = "mock"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://127.0.0.1:11434"
    llm_model: str = "gpt-4o-mini"

    # --- TTS ---
    tts_provider: Literal["elevenlabs", "openai", "piper", "mock"] = "mock"
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""

    # --- WhatsApp ---
    whatsapp_verify_token: str = "voicedesk-verify"
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""

    # --- Booking ---
    calendar_provider: Literal["google", "caldav", "internal", "mock"] = "internal"
    google_calendar_credentials_json: str = ""

    # --- Billing ---
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    @property
    def is_dev(self) -> bool:
        return self.env in ("dev", "test")

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()

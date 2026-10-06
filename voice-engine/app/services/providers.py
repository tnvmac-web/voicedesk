"""Provider abstractions for STT, LLM and TTS.

Each provider has a `mock` implementation so the engine runs with zero API
keys (dev/test). Real providers are thin adapters around the vendor SDK/HTTP
API and are selected via settings.
"""

from __future__ import annotations

import abc

import httpx

from app.config import get_settings

_settings = get_settings()


class LLMProvider(abc.ABC):
    @abc.abstractmethod
    async def complete(self, system: str, user: str) -> str:
        ...


class MockLLM(LLMProvider):
    """Deterministic LLM used in dev/test and as a graceful fallback.

    It does not 'think' — the receptionist service handles intents with rules
    and uses this only to phrase the reply.
    """

    async def complete(self, system: str, user: str) -> str:
        return user.strip() or "How can I help you today?"


class OpenAILLM(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    async def complete(self, system: str, user: str) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.4,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()


class OllamaLLM(LLMProvider):
    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def complete(self, system: str, user: str) -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"].strip()


class STTProvider(abc.ABC):
    @abc.abstractmethod
    async def transcribe(self, audio: bytes, content_type: str = "audio/wav") -> str:
        ...


class MockSTT(STTProvider):
    async def transcribe(self, audio: bytes, content_type: str = "audio/wav") -> str:
        return ""


class TTSProvider(abc.ABC):
    @abc.abstractmethod
    async def synthesize(self, text: str) -> bytes:
        ...


class MockTTS(TTSProvider):
    async def synthesize(self, text: str) -> bytes:
        # Silent WAV placeholder so callers get a valid audio container.
        return _silent_wav()


def _silent_wav(seconds: float = 0.2, rate: int = 8000) -> bytes:
    import struct

    n = int(seconds * rate)
    data = b"\x00\x00" * n
    header = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE"
    header += b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
    header += b"data" + struct.pack("<I", len(data))
    return header + data


def get_llm() -> LLMProvider:
    p = _settings.llm_provider
    if p == "openai" and _settings.openai_api_key:
        return OpenAILLM(_settings.openai_api_key, _settings.llm_model)
    if p == "ollama":
        return OllamaLLM(_settings.ollama_base_url, _settings.llm_model)
    return MockLLM()


def get_stt() -> STTProvider:
    return MockSTT()


def get_tts() -> TTSProvider:
    return MockTTS()

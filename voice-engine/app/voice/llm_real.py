"""Real LLM providers for Pipecat."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import httpx
from pipecat.frames.frames import Frame
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.services.llm_service import LLMService


class OpenAILLMService(LLMService):
    """OpenAI LLM (gpt-4o, gpt-4o-mini, etc.)."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "gpt-4o-mini",
        temperature: float = 0.4,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._api_key = api_key
        self._model = model
        self._temperature = temperature
        self._url = "https://api.openai.com/v1/chat/completions"

    async def completion(
        self,
        context: LLMContext,
        **kwargs,
    ) -> AsyncGenerator[Frame, None]:
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self._model,
            "messages": context.get_messages(),
            "temperature": self._temperature,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream("POST", self._url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        import json
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0]["delta"]
                            if "content" in delta and delta["content"]:
                                yield delta["content"]
                        except (json.JSONDecodeError, KeyError):
                            pass


class AnthropicLLMService(LLMService):
    """Anthropic Claude (3.5 Sonnet / 3 Haiku)."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.4,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._api_key = api_key
        self._model = model
        self._temperature = temperature
        self._url = "https://api.anthropic.com/v1/messages"

    async def completion(
        self,
        context: LLMContext,
        **kwargs,
    ) -> AsyncGenerator[Frame, None]:
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        messages = [m for m in context.get_messages() if m["role"] != "system"]
        system = next((m["content"] for m in context.get_messages() if m["role"] == "system"), "")
        payload = {
            "model": self._model,
            "messages": messages,
            "system": system,
            "temperature": self._temperature,
            "max_tokens": 1024,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream("POST", self._url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        import json
                        try:
                            chunk = json.loads(data)
                            if chunk.get("type") == "content_block_delta":
                                text = chunk["delta"].get("text", "")
                                if text:
                                    yield text
                        except (json.JSONDecodeError, KeyError):
                            pass


class OllamaLLMService(LLMService):
    """Local Ollama LLM (no API key needed)."""

    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "llama3.1:8b",
        temperature: float = 0.4,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._temperature = temperature

    async def completion(
        self,
        context: LLMContext,
        **kwargs,
    ) -> AsyncGenerator[Frame, None]:
        payload = {
            "model": self._model,
            "messages": context.get_messages(),
            "temperature": self._temperature,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST", f"{self._base_url}/api/chat", json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.strip():
                        import json
                        try:
                            chunk = json.loads(line)
                            msg = chunk.get("message", {})
                            if "content" in msg:
                                yield msg["content"]
                        except json.JSONDecodeError:
                            pass


def get_llm_from_settings() -> LLMService:
    """Factory: returns the configured LLM service."""
    from app.config import get_settings
    s = get_settings()
    if s.llm_provider == "openai" and s.openai_api_key:
        return OpenAILLMService(s.openai_api_key, model=s.llm_model)
    if s.llm_provider == "anthropic" and s.anthropic_api_key:
        return AnthropicLLMService(s.anthropic_api_key, model=s.llm_model)
    if s.llm_provider == "ollama":
        return OllamaLLMService(base_url=s.ollama_base_url, model=s.llm_model)
    from app.services.providers import MockLLM
    return MockLLM()
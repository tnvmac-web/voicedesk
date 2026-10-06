"""Real STT providers for Pipecat."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import httpx
from pipecat.frames.frames import Frame, TranscriptionFrame
from pipecat.services.stt_service import STTService


class DeepgramSTTService(STTService):
    """Deepgram Nova-2 streaming STT.

    See: https://developers.deepgram.com/docs/streaming-audio
    """

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "nova-2",
        language: str = "en",
        punctuate: bool = True,
        smart_format: bool = True,
        interim_results: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._api_key = api_key
        self._model = model
        self._language = language
        self._punctuate = punctuate
        self._smart_format = smart_format
        self._interim_results = interim_results
        self._url = (
            f"wss://api.deepgram.com/v1/listen?model={model}"
            f"&language={language}&punctuate={str(punctuate).lower()}"
            f"&smart_format={str(smart_format).lower()}"
            f"&interim_results={str(interim_results).lower()}"
        )

    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame | None, None]:
        # Note: Deepgram streaming requires WebSocket. This placeholder
        # shows the integration shape; real implementation uses
        # websockets library with an async generator feeding audio chunks.
        # For production, swap this with a persistent WebSocket connection.
        yield TranscriptionFrame(
            text="",
            user_id="caller",
            timestamp="",
            finalized=False,
        )

    async def _streaming_loop(self, audio_queue, websocket) -> None:
        """Internal: the real streaming implementation (sketched)."""
        async with httpx.AsyncClient() as client:
            pass  # would open ws and forward audio chunks


class WhisperSTTService(STTService):
    """Local Whisper (via whisper.cpp / faster-whisper) STT.

    Runs entirely on the server; no API key or network required.
    """

    def __init__(
        self,
        *,
        model_size: str = "base.en",
        device: str = "cpu",
        compute_type: str = "int8",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._model = None

    def _lazy_load(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self._model_size, device=self._device, compute_type=self._compute_type
            )

    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame | None, None]:
        # Convert PCM to WAV for faster-whisper
        import io
        import wave
        wav = io.BytesIO()
        with wave.open(wav, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(audio)
        wav_bytes = wav.getvalue()

        self._lazy_load()
        segments, _ = await asyncio.to_thread(
            self._model.transcribe, io.BytesIO(wav_bytes), beam_size=5, vad_filter=True
        )
        text = " ".join(s.text for s in segments).strip()
        if text:
            yield TranscriptionFrame(
                text=text,
                user_id="caller",
                timestamp="",
                finalized=True,
            )


def get_stt_from_settings() -> STTService:
    """Factory: returns the configured STT service."""
    from app.config import get_settings
    s = get_settings()
    if s.stt_provider == "deepgram" and s.deepgram_api_key:
        return DeepgramSTTService(s.deepgram_api_key)
    if s.stt_provider == "whisper":
        return WhisperSTTService()
    from app.voice.stt import MockSTTService
    return MockSTTService()
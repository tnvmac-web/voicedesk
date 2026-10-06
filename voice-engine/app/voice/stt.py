"""Mock speech-to-text service for Pipecat.

Returns an empty transcript so the pipeline is exercisable with zero API
keys. Real providers (Deepgram/Whisper) plug in by swapping this class.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from pipecat.frames.frames import Frame
from pipecat.services.stt_service import STTService


class MockSTTService(STTService):
    """STT that yields no transcription (dev / test / silent mode)."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame | None, None]:  # noqa: ARG002
        yield None

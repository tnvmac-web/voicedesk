"""Mock text-to-speech service for Pipecat.

Emits a short silent PCM buffer per text frame so the pipeline produces
audio output without any TTS provider. Real providers (ElevenLabs/OpenAI)
plug in by swapping this class.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from pipecat.frames.frames import Frame, TTSAudioRawFrame, TTSStartedFrame, TTSStoppedFrame
from pipecat.services.tts_service import TTSService

SAMPLE_RATE = 24000


def silence_pcm(seconds: float = 0.25, rate: int = SAMPLE_RATE) -> bytes:
    """Signed 16-bit mono PCM silence."""
    return b"\x00\x00" * int(seconds * rate)


class MockTTSService(TTSService):
    """TTS that emits silent audio sized to the spoken text."""

    def __init__(self, **kwargs) -> None:
        super().__init__(sample_rate=SAMPLE_RATE, **kwargs)

    async def run_tts(self, text: str, context_id: str) -> AsyncGenerator[Frame | None, None]:
        yield TTSStartedFrame(context_id=context_id)
        # ~14 chars/sec of speech, clamped so short replies still produce audio.
        seconds = max(0.4, min(8.0, len(text) / 14.0))
        yield TTSAudioRawFrame(
            audio=silence_pcm(seconds),
            sample_rate=SAMPLE_RATE,
            num_channels=1,
            context_id=context_id,
        )
        yield TTSStoppedFrame(context_id=context_id)

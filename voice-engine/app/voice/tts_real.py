"""Real TTS providers for Pipecat."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import httpx
from pipecat.frames.frames import Frame, TTSAudioRawFrame, TTSStartedFrame, TTSStoppedFrame
from pipecat.services.tts_service import TextAggregationMode, TTSService


class ElevenLabsTTSService(TTSService):
    """ElevenLabs streaming TTS.

    See: https://elevenlabs.io/docs/api-reference/text-to-speech/stream
    """

    def __init__(
        self,
        api_key: str,
        *,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",  # Rachel
        model_id: str = "eleven_flash_v2_5",
        output_format: str = "pcm_24000",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        **kwargs,
    ) -> None:
        super().__init__(
            sample_rate=24000,
            text_aggregation_mode=TextAggregationMode.SENTENCES,
            push_text_frames=True,
            **kwargs,
        )
        self._api_key = api_key
        self._voice_id = voice_id
        self._model_id = model_id
        self._output_format = output_format
        self._stability = stability
        self._similarity_boost = similarity_boost
        self._url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"

    async def run_tts(self, text: str, context_id: str) -> AsyncGenerator[Frame | None, None]:
        yield TTSStartedFrame(context_id=context_id)

        headers = {
            "xi-api-key": self._api_key,
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": self._model_id,
            "voice_settings": {
                "stability": self._stability,
                "similarity_boost": self._similarity_boost,
            },
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(self._url, headers=headers, json=payload)
            resp.raise_for_status()
            # ElevenLabs returns MP3; decode to PCM
            import io

            from pydub import AudioSegment
            mp3 = io.BytesIO(resp.content)
            seg = AudioSegment.from_mp3(mp3).set_frame_rate(24000).set_channels(1).set_sample_width(2)
            pcm = seg.raw_data
            yield TTSAudioRawFrame(
                audio=pcm,
                sample_rate=24000,
                num_channels=1,
                context_id=context_id,
            )

        yield TTSStoppedFrame(context_id=context_id)


class OpenAITTSService(TTSService):
    """OpenAI TTS (tts-1 / tts-1-hd)."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "tts-1",
        voice: str = "alloy",
        **kwargs,
    ) -> None:
        super().__init__(
            sample_rate=24000,
            text_aggregation_mode=TextAggregationMode.SENTENCES,
            push_text_frames=True,
            **kwargs,
        )
        self._api_key = api_key
        self._model = model
        self._voice = voice
        self._url = "https://api.openai.com/v1/audio/speech"

    async def run_tts(self, text: str, context_id: str) -> AsyncGenerator[Frame | None, None]:
        yield TTSStartedFrame(context_id=context_id)

        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        payload = {"model": self._model, "voice": self._voice, "input": text, "response_format": "mp3"}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(self._url, headers=headers, json=payload)
            resp.raise_for_status()
            import io

            from pydub import AudioSegment
            mp3 = io.BytesIO(resp.content)
            seg = AudioSegment.from_mp3(mp3).set_frame_rate(24000).set_channels(1).set_sample_width(2)
            pcm = seg.raw_data
            yield TTSAudioRawFrame(
                audio=pcm,
                sample_rate=24000,
                num_channels=1,
                context_id=context_id,
            )

        yield TTSStoppedFrame(context_id=context_id)


def get_tts_from_settings() -> TTSService:
    """Factory: returns the configured TTS service."""
    from app.config import get_settings
    s = get_settings()
    if s.tts_provider == "elevenlabs" and s.elevenlabs_api_key:
        return ElevenLabsTTSService(s.elevenlabs_api_key, voice_id=s.elevenlabs_voice_id)
    if s.tts_provider == "openai" and s.openai_api_key:
        return OpenAITTSService(s.openai_api_key)
    from app.voice.tts import MockTTSService
    return MockTTSService()
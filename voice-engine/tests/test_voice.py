"""Tests for the Pipecat voice pipeline and receptionist processor."""

from __future__ import annotations

import asyncio

from pipecat.frames.frames import TextFrame, TranscriptionFrame
from sqlalchemy.orm import Session

from app.models import AgentConfig, Tenant
from app.services.receptionist import handle_turn
from app.voice.receptionist_processor import ReceptionistProcessor
from app.voice.stt import MockSTTService
from app.voice.tts import MockTTSService, silence_pcm


def _make_tenant(db: Session) -> Tenant:
    tenant = Tenant(name="Pipeline Dental", slug="pipeline-dental", vertical="dental")
    db.add(tenant)
    db.flush()
    db.add(AgentConfig(tenant_id=tenant.id, name="Receptionist"))
    db.commit()
    return tenant


def test_mock_stt_yields_nothing() -> None:
    async def run() -> list:
        svc = MockSTTService()
        return [f async for f in svc.run_stt(b"\x00\x00" * 160)]

    frames = asyncio.run(run())
    assert all(f is None for f in frames)


def test_mock_tts_produces_audio_frames() -> None:
    async def run() -> list:
        svc = MockTTSService()
        return [f async for f in svc.run_tts("Hello there, how can I help?", "ctx-1")]

    frames = asyncio.run(run())
    kinds = {type(f).__name__ for f in frames}
    assert "TTSStartedFrame" in kinds
    assert "TTSAudioRawFrame" in kinds
    assert "TTSStoppedFrame" in kinds


def test_silence_pcm_is_valid() -> None:
    data = silence_pcm(0.1)
    assert len(data) == int(0.1 * 24000) * 2
    assert set(data) == {0}


def test_receptionist_processor_handles_transcript(db: Session) -> None:
    tenant = _make_tenant(db)
    proc = ReceptionistProcessor(db=db, tenant=tenant)

    pushed: list[TextFrame] = []
    proc.push_frame = _capture(pushed)  # type: ignore[assignment]

    async def run() -> None:
        from pipecat.processors.frame_processor import FrameDirection

        await proc.process_frame(
            TranscriptionFrame(text="I want to book a cleaning", user_id="u1", timestamp=""),
            FrameDirection.DOWNSTREAM,
        )

    asyncio.run(run())
    assert proc.last_intent == "booking"
    assert proc.last_action == "appointment_created"
    assert pushed and "booked" in pushed[0].text.lower()


def test_receptionist_processor_passes_through_non_text(db: Session) -> None:
    tenant = _make_tenant(db)
    proc = ReceptionistProcessor(db=db, tenant=tenant)
    pushed: list = []
    proc.push_frame = _capture(pushed)  # type: ignore[assignment]

    from pipecat.frames.frames import AudioRawFrame
    from pipecat.processors.frame_processor import FrameDirection

    audio = AudioRawFrame(audio=b"\x00\x00" * 80, sample_rate=8000, num_channels=1)
    asyncio.run(proc.process_frame(audio, FrameDirection.DOWNSTREAM))
    assert len(pushed) == 1
    assert isinstance(pushed[0], AudioRawFrame)


def test_handle_turn_hours_intent(db: Session) -> None:
    tenant = _make_tenant(db)

    async def run():
        return await handle_turn(db, tenant, "what are your opening hours?")

    result = asyncio.run(run())
    assert result.intent == "hours"
    assert "09:00-17:00" in result.reply


def _capture(sink: list):
    async def _push(frame, direction=None):
        sink.append(frame)

    return _push

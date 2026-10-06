"""Builds the VoiceDesk Pipecat pipeline.

Flow:  transport.input -> STT -> ReceptionistProcessor -> TTS -> transport.output

The transport, STT and TTS are swappable: dev uses mock services and a local
WebSocket transport; production swaps in Twilio/Telnyx + Deepgram + ElevenLabs
without touching the receptionist brain.

Uses the current Pipecat 1.12 worker API (PipelineWorker). The older
PipelineTask/PipelineRunner pair is deprecated and will be removed in 2.0.
"""

from __future__ import annotations

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.transports.base_transport import BaseTransport
from sqlalchemy.orm import Session

from app.models import AgentConfig, Call, Tenant
from app.voice.receptionist_processor import ReceptionistProcessor
from app.voice.stt import MockSTTService
from app.voice.tts import MockTTSService


def build_pipeline(
    transport: BaseTransport,
    db: Session,
    tenant: Tenant,
    agent: AgentConfig | None = None,
    call: Call | None = None,
    caller_phone: str = "",
    stt: FrameProcessor | None = None,
    tts: FrameProcessor | None = None,
    with_services: bool = True,
) -> tuple[Pipeline, PipelineWorker, ReceptionistProcessor]:
    """Assemble the pipeline and return it with its worker and brain processor."""
    stt_service = stt or MockSTTService()
    tts_service = tts or MockTTSService()
    brain = ReceptionistProcessor(
        db=db, tenant=tenant, agent=agent, call=call, caller_phone=caller_phone
    )

    stages: list[FrameProcessor] = [transport.input()]
    if with_services:
        stages += [stt_service, brain, tts_service]
    else:
        # Test/simulation mode: brain only, so frames injected at the head
        # reach the receptionist without an STT consuming them.
        stages += [brain]
    stages += [transport.output()]

    pipeline = Pipeline(stages)
    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=8000,
            audio_out_sample_rate=24000,
            enable_metrics=True,
        ),
    )
    return pipeline, worker, brain

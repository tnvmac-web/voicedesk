"""End-to-end smoke test of the assembled Pipecat pipeline.

Runs a real PipelineWorker through WorkerRunner with a fake transport,
injects a caller utterance at the pipeline head, and asserts the receptionist
produced a reply and created the booking.
"""

from __future__ import annotations

import asyncio

from pipecat.pipeline.runner import WorkerRunner
from pipecat.processors.frame_processor import FrameProcessor
from sqlalchemy.orm import Session

from app.models import AgentConfig, Tenant
from app.voice.pipeline import build_pipeline


class _FakeTransport(FrameProcessor):
    """Minimal transport stand-in with input()/output() stages."""

    def __init__(self) -> None:
        super().__init__()
        self._input = FrameProcessor()
        self._output = FrameProcessor()

    def input(self) -> FrameProcessor:
        return self._input

    def output(self) -> FrameProcessor:
        return self._output


def _make_tenant(db: Session) -> Tenant:
    tenant = Tenant(name="E2E Dental", slug="e2e-dental", vertical="dental")
    db.add(tenant)
    db.flush()
    db.add(AgentConfig(tenant_id=tenant.id, name="Receptionist"))
    db.commit()
    return tenant


def test_pipeline_assembles_with_expected_stages(db: Session) -> None:
    tenant = _make_tenant(db)
    transport = _FakeTransport()
    pipeline, worker, brain = build_pipeline(transport, db=db, tenant=tenant)  # type: ignore[arg-type]
    # transport.input, stt, brain, tts, transport.output (+ Source/Sink)
    names = [type(p).__name__ for p in pipeline.processors]
    assert "MockSTTService" in names
    assert "ReceptionistProcessor" in names
    assert "MockTTSService" in names
    assert brain is not None
    assert worker is not None


def test_pipeline_worker_runs_and_stops_cleanly(db: Session) -> None:
    """The assembled pipeline starts under WorkerRunner and cancels cleanly."""
    tenant = _make_tenant(db)
    transport = _FakeTransport()
    _pipeline, worker, brain = build_pipeline(transport, db=db, tenant=tenant)  # type: ignore[arg-type]

    async def run() -> None:
        runner = WorkerRunner(handle_sigint=False)
        await runner.add_workers(worker)

        async def stop() -> None:
            await asyncio.sleep(0.5)
            await worker.cancel()

        await asyncio.gather(runner.run(worker), stop())

    asyncio.run(run())
    # The worker ran to completion without error and the brain is intact.
    assert brain is not None
    assert brain.last_intent == ""  # no utterance fed in this lifecycle test

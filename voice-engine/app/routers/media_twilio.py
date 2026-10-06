"""Twilio Media Streams WebSocket endpoint.

Receives audio from Twilio, runs the VoiceDesk pipeline (STT -> Receptionist -> TTS),
and streams TTS audio back to Twilio in real time.

See: https://www.twilio.com/docs/voice/media-streams
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import AgentConfig, Call, Tenant
from app.voice.pipeline import build_pipeline
from app.voice.stt_real import get_stt_from_settings
from app.voice.tts_real import get_tts_from_settings

router = APIRouter(prefix="/media", tags=["media"])
_settings = get_settings()


class _TwilioTransport:
    """Minimal transport that wraps a WebSocket with Twilio's media stream protocol."""

    def __init__(self, websocket: WebSocket) -> None:
        self._ws = websocket
        self._input = _TwilioInput(self._ws)
        self._output = _TwilioOutput(self._ws)

    def input(self):
        return self._input

    def output(self):
        return self._output


class _TwilioInput:
    """Receives base64 PCM audio frames from Twilio and yields InputAudioRawFrame."""

    def __init__(self, websocket: WebSocket) -> None:
        self._ws = websocket

    async def __aiter__(self):
        async for msg in self._ws.iter_text():
            try:
                data = json.loads(msg)
                if data.get("event") == "media" and data.get("media", {}).get("payload"):
                    import base64
                    pcm = base64.b64decode(data["media"]["payload"])
                    from pipecat.frames.frames import InputAudioRawFrame
                    yield InputAudioRawFrame(
                        audio=pcm,
                        sample_rate=8000,
                        num_channels=1,
                    )
            except Exception:
                continue


class _TwilioOutput:
    """Sends TTS audio (PCM) to Twilio as base64 media frames."""

    def __init__(self, websocket: WebSocket) -> None:
        self._ws = websocket
        self._stream_sid = None

    async def send(self, frame) -> None:
        if not isinstance(frame, TTSAudioRawFrame):
            return
        if self._stream_sid is None:
            return
        import base64
        payload = base64.b64encode(frame.audio).decode("ascii")
        msg = {
            "event": "media",
            "streamSid": self._stream_sid,
            "media": {"payload": payload},
        }
        try:
            await self._ws.send_text(json.dumps(msg))
        except Exception:
            pass


def set_stream_sid(transport: _TwilioTransport, stream_sid: str) -> None:
    transport._output._stream_sid = stream_sid


@router.websocket("/twilio")
async def twilio_media_stream(
    websocket: WebSocket,
    db: Session = Depends(get_db),
) -> None:
    await websocket.accept()

    # Read the first message to get the tenant (via streamSid or To number).
    # In production, match the To number to a tenant.
    tenant = db.query(Tenant).filter(Tenant.is_active.is_(True)).first()
    if tenant is None:
        await websocket.close()
        return

    agent = (
        db.query(AgentConfig)
        .filter(AgentConfig.tenant_id == tenant.id, AgentConfig.is_active.is_(True))
        .first()
    )
    call = Call(
        tenant_id=tenant.id,
        provider="twilio",
        direction="inbound",
        status="active",
    )
    db.add(call)
    db.commit()

    transport = _TwilioTransport(websocket)
    stt = get_stt_from_settings()
    tts = get_tts_from_settings()
    pipeline, worker, brain = build_pipeline(
        transport, db=db, tenant=tenant, agent=agent, call=call, stt=stt, tts=tts
    )

    from pipecat.pipeline.runner import WorkerRunner
    runner = WorkerRunner(handle_sigint=False)
    await runner.add_workers(worker)

    # Tell Twilio the streamSid once we get it from the 'start' event.
    stream_sid = None

    async def run_pipeline():
        try:
            await runner.run(worker)
        except Exception:
            pass

    pipeline_task = asyncio.create_task(run_pipeline())

    try:
        async for msg in websocket.iter_text():
            data = json.loads(msg)
            event = data.get("event")

            if event == "start":
                stream_sid = data.get("start", {}).get("streamSid")
                if stream_sid:
                    transport._output._stream_sid = stream_sid
                    call.provider_call_id = stream_sid
                    db.commit()

            elif event == "media":
                # Frames are pushed to the pipeline via _TwilioInput's async iterator
                pass

            elif event == "stop":
                break

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        call.ended_at = __import__("datetime").datetime.now(__import__("datetime").UTC)
        call.status = "completed"
        db.commit()
        await worker.cancel()
        await pipeline_task
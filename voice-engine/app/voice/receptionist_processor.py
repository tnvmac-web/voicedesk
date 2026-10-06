"""The receptionist processor: the 'brain' stage of the voice pipeline.

Sits between STT and TTS. Receives the caller's transcript, runs it through
the receptionist service (intent + booking/lead side effects), then pushes the
reply text downstream for TTS to speak.
"""

from __future__ import annotations

from pipecat.frames.frames import Frame, TextFrame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from sqlalchemy.orm import Session

from app.models import AgentConfig, Call, Tenant
from app.services.receptionist import handle_turn


class ReceptionistProcessor(FrameProcessor):
    """Routes caller utterances through the VoiceDesk receptionist brain."""

    def __init__(
        self,
        db: Session,
        tenant: Tenant,
        agent: AgentConfig | None = None,
        call: Call | None = None,
        caller_phone: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._db = db
        self._tenant = tenant
        self._agent = agent
        self._call = call
        self._caller_phone = caller_phone
        self.last_intent: str = ""
        self.last_action: str = ""

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)

        text = ""
        if isinstance(frame, TranscriptionFrame):
            text = frame.text
        elif isinstance(frame, TextFrame):
            text = frame.text

        if not text.strip():
            # Still forward non-text frames (audio, control) downstream.
            if not isinstance(frame, (TextFrame, TranscriptionFrame)):
                await self.push_frame(frame, direction)
            return

        result = await handle_turn(
            self._db,
            self._tenant,
            text,
            agent=self._agent,
            call=self._call,
            caller_phone=self._caller_phone,
        )
        self.last_intent = result.intent
        self.last_action = result.action
        await self.push_frame(TextFrame(text=result.reply), FrameDirection.DOWNSTREAM)

"""Telephony webhooks.

Implements the provider-agnostic call flow plus the two ROI features that
differentiate VoiceDesk:

- **Missed-call text-back**: when a call is missed, auto-send an SMS/WhatsApp
  so the lead is captured instead of lost (60%+ of callers dial the next
  provider on voicemail).
- **After-hours mode**: outside business hours the AI answers and books.

Provider adapters (Twilio/Vonage/Telnyx) share the same handler; the mock
provider is used in dev.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Form, Request, Response
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import AgentConfig, Call, Contact, Conversation, Message, Tenant

router = APIRouter(prefix="/telephony", tags=["telephony"])
_settings = get_settings()


def _twiml(text: str) -> Response:
    body = f'<?xml version="1.0" encoding="UTF-8"?><Response><Say>{text}</Say></Response>'
    return Response(content=body, media_type="application/xml")


def _find_tenant_by_number(db: Session, to_number: str) -> Tenant | None:
    tenant = db.query(Tenant).filter(Tenant.phone_number == to_number).first()
    if tenant is None:
        tenant = db.query(Tenant).filter(Tenant.is_active.is_(True)).first()
    return tenant


@router.post("/voice")
async def voice_webhook(
    request: Request,
    db: Session = Depends(get_db),
    From: str = Form(default=""),  # noqa: N803 - Twilio form field names
    To: str = Form(default=""),  # noqa: N803
    CallSid: str = Form(default=""),  # noqa: N803
) -> Response:
    """Entry point for an inbound call. Returns TwiML greeting."""
    tenant = _find_tenant_by_number(db, To)
    if tenant is None:
        return _twiml("Sorry, this number is not configured.")

    agent = (
        db.query(AgentConfig)
        .filter(AgentConfig.tenant_id == tenant.id, AgentConfig.is_active.is_(True))
        .first()
    )
    call = Call(
        tenant_id=tenant.id,
        provider=_settings.telephony_provider,
        provider_call_id=CallSid,
        direction="inbound",
        status="active",
        from_number=From,
        to_number=To,
    )
    db.add(call)
    db.commit()

    greeting = agent.greeting if agent and agent.greeting else (
        f"Thank you for calling {tenant.name}. How can I help you today?"
    )
    return _twiml(greeting)


@router.post("/status")
async def call_status(
    db: Session = Depends(get_db),
    CallSid: str = Form(default=""),  # noqa: N803
    CallStatus: str = Form(default=""),  # noqa: N803
    CallDuration: str = Form(default="0"),  # noqa: N803
    From: str = Form(default=""),  # noqa: N803
    To: str = Form(default=""),  # noqa: N803
) -> dict[str, str]:
    """Call status callback. Triggers missed-call text-back on no-answer."""
    call = (
        db.query(Call).filter(Call.provider_call_id == CallSid).first()
        if CallSid
        else None
    )
    tenant = call.tenant if call else _find_tenant_by_number(db, To)
    if tenant is None:
        return {"status": "ignored"}

    if call is None:
        call = Call(tenant_id=tenant.id, provider_call_id=CallSid, from_number=From, to_number=To)
        db.add(call)

    call.status = CallStatus or call.status
    try:
        call.duration_seconds = int(CallDuration or 0)
    except ValueError:
        call.duration_seconds = 0
    if CallStatus in ("completed", "no-answer", "busy", "failed", "canceled"):
        call.ended_at = datetime.now(UTC)

    textback_sent = False
    if CallStatus in ("no-answer", "busy", "failed", "canceled"):
        agent = (
            db.query(AgentConfig)
            .filter(AgentConfig.tenant_id == tenant.id, AgentConfig.is_active.is_(True))
            .first()
        )
        if agent and agent.missed_call_textback and From:
            contact = (
                db.query(Contact)
                .filter(Contact.tenant_id == tenant.id, Contact.phone == From)
                .first()
            )
            if contact is None:
                contact = Contact(
                    tenant_id=tenant.id, phone=From, channel="sms", is_lead=True
                )
                db.add(contact)
                db.flush()
            conv = (
                db.query(Conversation)
                .filter(Conversation.tenant_id == tenant.id, Conversation.contact_id == contact.id)
                .first()
            )
            if conv is None:
                conv = Conversation(tenant_id=tenant.id, contact_id=contact.id, channel="sms")
                db.add(conv)
                db.flush()
            body = (
                f"Sorry we missed your call to {tenant.name}! "
                "Reply here and we'll get right back to you, or tell us a time that suits."
            )
            db.add(
                Message(conversation_id=conv.id, direction="outbound", sender="ai", body=body)
            )
            conv.last_message_at = datetime.now(UTC)
            call.outcome = "missed_textback"
            textback_sent = True

    db.commit()
    return {"status": "ok", "textback_sent": str(textback_sent).lower()}

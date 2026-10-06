"""Receptionist brain.

Turns an inbound caller utterance into an intent, an optional side effect
(book an appointment, capture a lead) and a spoken reply.

Intent handling is rule-based so it works with zero API keys and is fully
testable; the configured LLM is used to phrase replies when available.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import AgentConfig, Appointment, Call, Contact, Tenant
from app.services.providers import get_llm

BOOKING_WORDS = ("book", "appointment", "schedule", "reserve", "slot", "visit")
PRICE_WORDS = ("price", "cost", "how much", "fee", "charge", "rate")
HOURS_WORDS = ("open", "hours", "when are you", "closing", "close")
HUMAN_WORDS = ("human", "person", "agent", "manager", "speak to someone", "real person")
EMERGENCY_WORDS = ("emergency", "urgent", "asap", "right now", "flood", "leak", "broken")

_TIME_RE = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", re.IGNORECASE)


@dataclass
class TurnResult:
    reply: str
    intent: str
    action: str = ""
    appointment_id: str | None = None
    contact_id: str | None = None


def detect_intent(text: str) -> str:
    t = text.lower()
    if any(w in t for w in EMERGENCY_WORDS):
        return "emergency"
    if any(w in t for w in BOOKING_WORDS):
        return "booking"
    if any(w in t for w in PRICE_WORDS):
        return "pricing"
    if any(w in t for w in HOURS_WORDS):
        return "hours"
    if any(w in t for w in HUMAN_WORDS):
        return "human_handoff"
    return "general"


def _parse_time(text: str) -> datetime | None:
    m = _TIME_RE.search(text)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    ampm = (m.group(3) or "").lower()
    if ampm == "pm" and hour < 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0
    if not (0 <= hour <= 23):
        return None
    now = datetime.now(UTC)
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def _get_or_create_contact(db: Session, tenant: Tenant, phone: str, name: str = "") -> Contact:
    contact = None
    if phone:
        contact = (
            db.query(Contact)
            .filter(Contact.tenant_id == tenant.id, Contact.phone == phone)
            .first()
        )
    if contact is None:
        contact = Contact(tenant_id=tenant.id, phone=phone, name=name or "Caller", channel="voice")
        db.add(contact)
        db.flush()
    return contact


def _default_greeting(tenant: Tenant) -> str:
    return f"Thank you for calling {tenant.name}. How can I help you today?"


async def handle_turn(
    db: Session,
    tenant: Tenant,
    text: str,
    agent: AgentConfig | None = None,
    call: Call | None = None,
    caller_phone: str = "",
) -> TurnResult:
    """Process one caller utterance and return the reply + side effects."""
    intent = detect_intent(text)
    contact = _get_or_create_contact(db, tenant, caller_phone)
    action = ""
    appointment_id: str | None = None

    if intent == "booking":
        starts = _parse_time(text) or (datetime.now(UTC) + timedelta(days=1)).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        appt = Appointment(
            tenant_id=tenant.id,
            contact_id=contact.id,
            call_id=call.id if call else None,
            title="Appointment",
            service=text[:180],
            starts_at=starts,
            source="voice",
        )
        db.add(appt)
        db.flush()
        appointment_id = appt.id
        action = "appointment_created"
        reply = (
            f"I've booked you in for {starts.strftime('%A %d %B at %H:%M')}. "
            "Is there anything else I can help with?"
        )
    elif intent == "emergency":
        action = "human_handoff"
        reply = (
            "That sounds urgent — I'm flagging this for our on-call team right now. "
            "Please stay on the line."
        )
    elif intent == "human_handoff":
        action = "human_handoff"
        reply = "Of course — let me connect you to a member of our team."
    elif intent == "pricing":
        reply = "I can help with that. Which service are you interested in?"
    elif intent == "hours":
        hours = agent.business_hours if agent else "09:00-17:00"
        reply = f"We're open {hours}. Would you like to book a time?"
    else:
        # Let the configured LLM phrase a natural reply when available.
        system = agent.system_prompt if agent and agent.system_prompt else (
            f"You are the friendly AI receptionist for {tenant.name}."
        )
        llm = get_llm()
        try:
            reply = await llm.complete(system, text)
        except Exception:  # noqa: BLE001 - never fail a call on LLM error
            reply = "I'm sorry, could you say that again?"

    if call is not None:
        if call.outcome == "":
            call.outcome = {
                "booking": "booked",
                "emergency": "escalated",
                "human_handoff": "escalated",
            }.get(intent, "info")

    db.commit()
    return TurnResult(
        reply=reply,
        intent=intent,
        action=action,
        appointment_id=appointment_id,
        contact_id=contact.id,
    )

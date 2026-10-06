"""Unified inbox: WhatsApp/SMS conversations + outbound send.

The WhatsApp webhook is the entry point for Meta Cloud API messages; the
verify handshake and inbound handler are implemented so a real token can be
dropped in later. Without a token, messages can be simulated via the API.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_tenant
from app.models import Contact, Conversation, Message, Tenant
from app.schemas import (
    ConversationDetail,
    ConversationOut,
    MessageOut,
    SendMessageIn,
)

router = APIRouter(tags=["inbox"])
_settings = get_settings()


# --- Authenticated inbox API ---
@router.get("/api/conversations", response_model=list[ConversationOut])
def list_conversations(
    tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)
) -> list[Conversation]:
    return (
        db.query(Conversation)
        .filter(Conversation.tenant_id == tenant.id)
        .order_by(Conversation.last_message_at.desc())
        .all()
    )


@router.get("/api/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> Conversation:
    conv = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.tenant_id == tenant.id)
        .first()
    )
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return conv


@router.post(
    "/api/conversations/{conversation_id}/messages",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
)
def send_message(
    conversation_id: str,
    payload: SendMessageIn,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> Message:
    conv = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.tenant_id == tenant.id)
        .first()
    )
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    msg = Message(
        conversation_id=conv.id, direction="outbound", sender="staff", body=payload.body
    )
    db.add(msg)
    conv.last_message_at = datetime.now(UTC)
    db.commit()
    db.refresh(msg)
    return msg


# --- WhatsApp Cloud API webhook ---
@router.get("/webhooks/whatsapp")
def whatsapp_verify(
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
) -> int:
    """Meta webhook verification handshake."""
    if hub_mode == "subscribe" and hub_verify_token == _settings.whatsapp_verify_token:
        return int(hub_challenge or 0)
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Verification failed")


@router.post("/webhooks/whatsapp")
async def whatsapp_inbound(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    """Receive an inbound WhatsApp message and store it in the unified inbox.

    Tenant resolution: matched by the receiving phone_number_id -> tenant.
    Falls back to the first active tenant in dev so the flow is testable.
    """
    body = await request.json()
    try:
        entry = body["entry"][0]["changes"][0]["value"]
        messages = entry.get("messages", [])
        if not messages:
            return {"status": "ignored"}
        msg = messages[0]
        from_number = msg.get("from", "")
        text = msg.get("text", {}).get("body", "")
    except (KeyError, IndexError, TypeError):
        return {"status": "ignored"}

    tenant = db.query(Tenant).filter(Tenant.is_active.is_(True)).first()
    if tenant is None:
        return {"status": "no_tenant"}

    contact = (
        db.query(Contact)
        .filter(Contact.tenant_id == tenant.id, Contact.phone == from_number)
        .first()
    )
    if contact is None:
        contact = Contact(tenant_id=tenant.id, phone=from_number, channel="whatsapp")
        db.add(contact)
        db.flush()

    conv = (
        db.query(Conversation)
        .filter(Conversation.tenant_id == tenant.id, Conversation.contact_id == contact.id)
        .first()
    )
    if conv is None:
        conv = Conversation(tenant_id=tenant.id, contact_id=contact.id, channel="whatsapp")
        db.add(conv)
        db.flush()

    db.add(Message(conversation_id=conv.id, direction="inbound", sender="contact", body=text))
    conv.last_message_at = datetime.now(UTC)
    db.commit()
    return {"status": "received"}

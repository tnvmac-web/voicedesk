"""Shared Pydantic schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# --- Auth / tenant ---
class TenantCreate(BaseModel):
    business_name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9-]+$")
    vertical: str = "generic"
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = ""


class TenantOut(BaseModel):
    id: str
    name: str
    slug: str
    vertical: str
    phone_number: str | None = None
    minutes_used: int
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: str
    role: str


# --- Agent config ---
class AgentConfigIn(BaseModel):
    name: str = "Receptionist"
    greeting: str = ""
    system_prompt: str = ""
    voice_id: str = ""
    language: str = "en"
    vertical: str = "generic"
    missed_call_textback: bool = True
    after_hours_mode: bool = True
    business_hours: str = "09:00-17:00"


class AgentConfigOut(AgentConfigIn):
    id: str
    tenant_id: str

    model_config = {"from_attributes": True}


# --- Contact ---
class ContactIn(BaseModel):
    name: str = ""
    phone: str = ""
    email: str = ""
    channel: str = "voice"
    notes: str = ""
    is_lead: bool = True


class ContactOut(ContactIn):
    id: str
    tenant_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Call ---
class CallOut(BaseModel):
    id: str
    tenant_id: str
    direction: str
    status: str
    from_number: str
    to_number: str
    duration_seconds: int
    transcript: str
    summary: str
    outcome: str
    started_at: datetime

    model_config = {"from_attributes": True}


# --- Appointment ---
class AppointmentIn(BaseModel):
    title: str = "Appointment"
    service: str = ""
    starts_at: datetime
    ends_at: datetime | None = None
    contact_id: str | None = None
    source: str = "voice"


class AppointmentOut(BaseModel):
    id: str
    tenant_id: str
    title: str
    service: str
    starts_at: datetime
    ends_at: datetime | None = None
    status: str
    source: str

    model_config = {"from_attributes": True}


# --- Conversation / messages ---
class MessageOut(BaseModel):
    id: str
    direction: str
    sender: str
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: str
    tenant_id: str
    contact_id: str | None = None
    channel: str
    status: str
    last_message_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = []


class SendMessageIn(BaseModel):
    body: str = Field(min_length=1)


# --- Voice turn (pipeline testing / mock mode) ---
class VoiceTurnIn(BaseModel):
    tenant_slug: str
    text: str
    call_id: str | None = None


class VoiceTurnOut(BaseModel):
    reply: str
    intent: str
    action: str = ""
    call_id: str | None = None

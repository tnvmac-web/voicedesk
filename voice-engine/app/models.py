"""ORM models — multi-tenant core for VoiceDesk.

Every business (tenant) owns: users, agent configs, contacts, calls,
appointments and conversations. Tenant scoping is applied in queries.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(UTC)


class Tenant(Base):
    """A business using VoiceDesk (multi-tenant root)."""

    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    vertical: Mapped[str] = mapped_column(String(50), default="generic")
    phone_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # usage metering
    minutes_used: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    users: Mapped[list[User]] = relationship(back_populates="tenant")
    agents: Mapped[list[AgentConfig]] = relationship(back_populates="tenant")
    contacts: Mapped[list[Contact]] = relationship(back_populates="tenant")
    calls: Mapped[list[Call]] = relationship(back_populates="tenant")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_user_tenant_email"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), default="")
    role: Mapped[str] = mapped_column(String(30), default="owner")  # owner|staff
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    tenant: Mapped[Tenant] = relationship(back_populates="users")


class AgentConfig(Base):
    """The AI receptionist configuration for a tenant (per vertical)."""

    __tablename__ = "agent_configs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), default="Receptionist")
    greeting: Mapped[str] = mapped_column(Text, default="")
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    voice_id: Mapped[str] = mapped_column(String(80), default="")
    language: Mapped[str] = mapped_column(String(10), default="en")
    vertical: Mapped[str] = mapped_column(String(50), default="generic")
    # feature toggles (the ROI features that differentiate VoiceDesk)
    missed_call_textback: Mapped[bool] = mapped_column(Boolean, default=True)
    after_hours_mode: Mapped[bool] = mapped_column(Boolean, default=True)
    business_hours: Mapped[str] = mapped_column(String(120), default="09:00-17:00")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    tenant: Mapped[Tenant] = relationship(back_populates="agents")


class Contact(Base):
    """A caller / lead / customer."""

    __tablename__ = "contacts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(40), default="", index=True)
    email: Mapped[str] = mapped_column(String(255), default="")
    channel: Mapped[str] = mapped_column(String(20), default="voice")  # voice|whatsapp|sms
    notes: Mapped[str] = mapped_column(Text, default="")
    is_lead: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    tenant: Mapped[Tenant] = relationship(back_populates="contacts")


class Call(Base):
    """A voice call handled by the AI receptionist."""

    __tablename__ = "calls"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    contact_id: Mapped[str | None] = mapped_column(ForeignKey("contacts.id"), nullable=True)
    provider: Mapped[str] = mapped_column(String(20), default="mock")
    provider_call_id: Mapped[str] = mapped_column(String(120), default="")
    direction: Mapped[str] = mapped_column(String(10), default="inbound")
    status: Mapped[str] = mapped_column(String(20), default="ringing")
    from_number: Mapped[str] = mapped_column(String(40), default="")
    to_number: Mapped[str] = mapped_column(String(40), default="")
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    transcript: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    outcome: Mapped[str] = mapped_column(String(40), default="")  # booked|lead|missed|info
    recording_url: Mapped[str] = mapped_column(String(500), default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant: Mapped[Tenant] = relationship(back_populates="calls")


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    contact_id: Mapped[str | None] = mapped_column(ForeignKey("contacts.id"), nullable=True)
    call_id: Mapped[str | None] = mapped_column(ForeignKey("calls.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), default="Appointment")
    service: Mapped[str] = mapped_column(String(200), default="")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="confirmed")
    source: Mapped[str] = mapped_column(String(20), default="voice")
    external_id: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Conversation(Base):
    """A WhatsApp/SMS thread (unified inbox)."""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    contact_id: Mapped[str | None] = mapped_column(ForeignKey("contacts.id"), nullable=True)
    channel: Mapped[str] = mapped_column(String(20), default="whatsapp")  # whatsapp|sms
    status: Mapped[str] = mapped_column(String(20), default="open")
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id"), index=True
    )
    direction: Mapped[str] = mapped_column(String(10), default="inbound")  # inbound|outbound
    sender: Mapped[str] = mapped_column(String(20), default="contact")  # contact|ai|staff
    body: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")

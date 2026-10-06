"""Create tables and optional demo seed data."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import Base, SessionLocal, engine
from app.models import AgentConfig, Call, Contact, Tenant, User
from app.security import hash_password


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def seed_demo(db: Session) -> None:
    """Create a demo tenant with agent, contacts, calls and appointments."""
    if db.query(Tenant).filter(Tenant.slug == "brightsmile-dental").first():
        return

    tenant = Tenant(
        name="BrightSmile Dental",
        slug="brightsmile-dental",
        vertical="dental",
        phone_number="+15550001234",
    )
    db.add(tenant)
    db.flush()

    db.add(
        User(
            tenant_id=tenant.id,
            email="demo@voicedesk.com",
            password_hash=hash_password("demo12345"),
            full_name="Demo Owner",
            role="owner",
        )
    )
    db.add(
        AgentConfig(
            tenant_id=tenant.id,
            name="Front Desk AI",
            greeting="Thanks for calling BrightSmile Dental! How can I help today?",
            system_prompt=(
                "You are the friendly front-desk receptionist for BrightSmile Dental. "
                "Book cleanings and consultations, answer opening-hours questions, and "
                "escalate emergencies to the on-call dentist."
            ),
            vertical="dental",
            business_hours="08:00-18:00",
        )
    )
    for name, phone in [("Alice Nguyen", "+15550009001"), ("Mark Rivera", "+15550009002")]:
        db.add(Contact(tenant_id=tenant.id, name=name, phone=phone, channel="voice"))

    db.add(
        Call(
            tenant_id=tenant.id,
            provider="simulator",
            direction="inbound",
            status="completed",
            from_number="+15550009001",
            to_number="+15550001234",
            duration_seconds=94,
            outcome="booked",
            transcript="caller: I'd like to book a cleaning\nai: I've booked you in.",
        )
    )
    db.commit()


def main() -> None:
    create_tables()
    db = SessionLocal()
    try:
        seed_demo(db)
        print("Database initialised and demo data seeded.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

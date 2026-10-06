"""Analytics: the ROI dashboard numbers that sell VoiceDesk.

Reports calls, bookings, leads, missed calls recovered, and an estimated
revenue-recovered figure using a configurable average job value.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_tenant
from app.models import Appointment, Call, Contact, Conversation, Tenant

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary")
def summary(
    days: int = Query(default=30, ge=1, le=365),
    avg_job_value: float = Query(default=150.0, ge=0),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> dict:
    since = datetime.now(UTC) - timedelta(days=days)

    calls = (
        db.query(func.count(Call.id))
        .filter(Call.tenant_id == tenant.id, Call.started_at >= since)
        .scalar()
        or 0
    )
    missed = (
        db.query(func.count(Call.id))
        .filter(
            Call.tenant_id == tenant.id,
            Call.started_at >= since,
            Call.outcome.in_(["missed", "missed_textback"]),
        )
        .scalar()
        or 0
    )
    bookings = (
        db.query(func.count(Appointment.id))
        .filter(Appointment.tenant_id == tenant.id, Appointment.starts_at >= since)
        .scalar()
        or 0
    )
    leads = (
        db.query(func.count(Contact.id))
        .filter(Contact.tenant_id == tenant.id, Contact.created_at >= since)
        .scalar()
        or 0
    )
    conversations = (
        db.query(func.count(Conversation.id))
        .filter(Conversation.tenant_id == tenant.id)
        .scalar()
        or 0
    )

    # Value model: every booking is a recovered job; every missed-call text-back
    # is a recovered lead worth a fraction of a job.
    recovered_leads = missed
    estimated_revenue_recovered = round(bookings * avg_job_value, 2)
    missed_call_recovery_rate = round((1 - (missed / calls)) * 100, 1) if calls else 100.0

    return {
        "window_days": days,
        "calls": calls,
        "missed_calls": missed,
        "missed_call_textbacks": missed,
        "bookings": bookings,
        "leads": leads,
        "conversations": conversations,
        "recovered_leads": recovered_leads,
        "answer_rate_pct": missed_call_recovery_rate,
        "estimated_revenue_recovered": estimated_revenue_recovered,
        "minutes_used": tenant.minutes_used,
    }

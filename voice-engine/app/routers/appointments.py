"""Appointments (booking)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_tenant
from app.models import Appointment, Tenant
from app.schemas import AppointmentIn, AppointmentOut

router = APIRouter(prefix="/api/appointments", tags=["appointments"])


@router.get("", response_model=list[AppointmentOut])
def list_appointments(
    tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)
) -> list[Appointment]:
    return (
        db.query(Appointment)
        .filter(Appointment.tenant_id == tenant.id)
        .order_by(Appointment.starts_at.asc())
        .all()
    )


@router.post("", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def create_appointment(
    payload: AppointmentIn,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> Appointment:
    appt = Appointment(tenant_id=tenant.id, **payload.model_dump())
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return appt


@router.post("/{appointment_id}/cancel", response_model=AppointmentOut)
def cancel_appointment(
    appointment_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> Appointment:
    appt = (
        db.query(Appointment)
        .filter(Appointment.id == appointment_id, Appointment.tenant_id == tenant.id)
        .first()
    )
    if appt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found")
    appt.status = "cancelled"
    db.commit()
    db.refresh(appt)
    return appt

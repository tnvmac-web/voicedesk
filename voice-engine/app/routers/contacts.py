"""Contacts (callers / leads / customers)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_tenant
from app.models import Contact, Tenant
from app.schemas import ContactIn, ContactOut

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


@router.get("", response_model=list[ContactOut])
def list_contacts(
    tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)
) -> list[Contact]:
    return (
        db.query(Contact)
        .filter(Contact.tenant_id == tenant.id)
        .order_by(Contact.created_at.desc())
        .all()
    )


@router.post("", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
def create_contact(
    payload: ContactIn,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> Contact:
    contact = Contact(tenant_id=tenant.id, **payload.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.get("/{contact_id}", response_model=ContactOut)
def get_contact(
    contact_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> Contact:
    contact = (
        db.query(Contact)
        .filter(Contact.id == contact_id, Contact.tenant_id == tenant.id)
        .first()
    )
    if contact is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contact not found")
    return contact

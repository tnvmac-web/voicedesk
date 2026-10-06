"""Signup, login and current-user endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import AgentConfig, Tenant, User
from app.schemas import LoginRequest, TenantCreate, TenantOut, TokenOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def signup(payload: TenantCreate, db: Session = Depends(get_db)) -> TokenOut:
    if db.query(Tenant).filter(Tenant.slug == payload.slug).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Slug already taken")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    tenant = Tenant(
        name=payload.business_name, slug=payload.slug, vertical=payload.vertical
    )
    db.add(tenant)
    db.flush()

    user = User(
        tenant_id=tenant.id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role="owner",
    )
    db.add(user)

    # Every tenant gets a default agent config.
    db.add(
        AgentConfig(
            tenant_id=tenant.id,
            name="Receptionist",
            greeting=f"Thank you for calling {tenant.name}. How can I help you today?",
            vertical=payload.vertical,
        )
    )
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, {"tenant_id": tenant.id, "role": user.role})
    return TokenOut(access_token=token, tenant_id=tenant.id, role=user.role)


@router.post("/login", response_model=TokenOut)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenOut:
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User disabled")
    token = create_access_token(user.id, {"tenant_id": user.tenant_id, "role": user.role})
    return TokenOut(access_token=token, tenant_id=user.tenant_id, role=user.role)


@router.get("/me", response_model=TenantOut)
def me(user: User = Depends(get_current_user)) -> Tenant:
    return user.tenant

"""Agent configuration endpoints (the AI receptionist settings)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_tenant
from app.models import AgentConfig, Tenant
from app.schemas import AgentConfigIn, AgentConfigOut

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.get("", response_model=list[AgentConfigOut])
def list_agents(
    tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)
) -> list[AgentConfig]:
    return db.query(AgentConfig).filter(AgentConfig.tenant_id == tenant.id).all()


@router.post("", response_model=AgentConfigOut, status_code=status.HTTP_201_CREATED)
def create_agent(
    payload: AgentConfigIn,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> AgentConfig:
    agent = AgentConfig(tenant_id=tenant.id, **payload.model_dump())
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.put("/{agent_id}", response_model=AgentConfigOut)
def update_agent(
    agent_id: str,
    payload: AgentConfigIn,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> AgentConfig:
    agent = (
        db.query(AgentConfig)
        .filter(AgentConfig.id == agent_id, AgentConfig.tenant_id == tenant.id)
        .first()
    )
    if agent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found")
    for key, value in payload.model_dump().items():
        setattr(agent, key, value)
    db.commit()
    db.refresh(agent)
    return agent

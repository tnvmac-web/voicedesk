"""Calls: list, detail, and the voice-turn simulator.

The `/api/calls/simulate` endpoint exercises the receptionist brain without
any telephony provider — used by the demo and the test suite.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_tenant
from app.models import AgentConfig, Call, Tenant
from app.schemas import CallOut, VoiceTurnIn, VoiceTurnOut
from app.services.receptionist import handle_turn

router = APIRouter(prefix="/api/calls", tags=["calls"])


@router.get("", response_model=list[CallOut])
def list_calls(
    tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)
) -> list[Call]:
    return (
        db.query(Call)
        .filter(Call.tenant_id == tenant.id)
        .order_by(Call.started_at.desc())
        .all()
    )


@router.get("/{call_id}", response_model=CallOut)
def get_call(
    call_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> Call:
    call = db.query(Call).filter(Call.id == call_id, Call.tenant_id == tenant.id).first()
    if call is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Call not found")
    return call


@router.post("/simulate", response_model=VoiceTurnOut)
async def simulate_turn(
    payload: VoiceTurnIn,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> VoiceTurnOut:
    """Process a caller utterance through the receptionist brain (no telephony)."""
    agent = (
        db.query(AgentConfig)
        .filter(AgentConfig.tenant_id == tenant.id, AgentConfig.is_active.is_(True))
        .first()
    )
    call = None
    if payload.call_id:
        call = (
            db.query(Call)
            .filter(Call.id == payload.call_id, Call.tenant_id == tenant.id)
            .first()
        )
    if call is None:
        call = Call(tenant_id=tenant.id, provider="simulator", direction="inbound", status="active")
        db.add(call)
        db.flush()

    result = await handle_turn(db, tenant, payload.text, agent=agent, call=call)
    call.transcript = (call.transcript + f"\ncaller: {payload.text}\nai: {result.reply}").strip()
    db.commit()
    return VoiceTurnOut(
        reply=result.reply,
        intent=result.intent,
        action=result.action,
        call_id=call.id,
    )

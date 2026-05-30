"""Suppression list endpoints: POST/GET/DELETE /v1/suppression."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from beacon.db.session import tenant_scoped_session
from beacon.services import suppression as svc

router = APIRouter(prefix="/suppression", tags=["suppression"])


IdentifierType = Literal["email", "phone_e164", "push_token", "device_id"]
ReasonType = Literal[
    "hard_bounce", "complaint", "unsubscribe", "manual", "dsar", "invalid", "blocked"
]


class SuppressionAdd(BaseModel):
    identifier_type: IdentifierType
    identifier_value: str = Field(..., min_length=1, max_length=512)
    reason: ReasonType = "manual"
    source_channel: str | None = Field(None, max_length=32)
    notes: str | None = None


class SuppressionOut(BaseModel):
    id: str
    identifier_type: str
    identifier_value: str
    reason: str
    source_channel: str | None
    created_at: datetime


def _require_org(request: Request) -> str:
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_required")
    return org_id


@router.post("", status_code=status.HTTP_201_CREATED, response_model=SuppressionOut)
async def add_entry(payload: SuppressionAdd, request: Request) -> SuppressionOut:
    org_id = _require_org(request)
    async with tenant_scoped_session(org_id) as session:
        row = await svc.add(
            session,
            organization_id=org_id,
            identifier_type=payload.identifier_type,
            identifier_value=payload.identifier_value,
            reason=payload.reason,
            source_channel=payload.source_channel,
            notes=payload.notes,
        )
    return SuppressionOut(
        id=row.id,
        identifier_type=row.identifier_type,
        identifier_value=row.identifier_value,
        reason=row.reason,
        source_channel=row.source_channel,
        created_at=row.created_at,
    )


@router.get("", response_model=list[SuppressionOut])
async def list_entries(
    request: Request,
    identifier_type: IdentifierType | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[SuppressionOut]:
    org_id = _require_org(request)
    async with tenant_scoped_session(org_id) as session:
        rows = await svc.list_entries(
            session,
            organization_id=org_id,
            identifier_type=identifier_type,
            limit=limit,
            offset=offset,
        )
    return [
        SuppressionOut(
            id=r.id,
            identifier_type=r.identifier_type,
            identifier_value=r.identifier_value,
            reason=r.reason,
            source_channel=r.source_channel,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def remove_entry(entry_id: str, request: Request) -> None:
    org_id = _require_org(request)
    async with tenant_scoped_session(org_id) as session:
        ok = await svc.remove(session, organization_id=org_id, entry_id=entry_id)
    if not ok:
        raise HTTPException(status_code=404, detail="entry_not_found")

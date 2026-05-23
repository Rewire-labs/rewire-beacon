"""Email domain endpoints: POST/GET /v1/domains + POST /v1/domains/{id}/verify."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from beacon.db.session import tenant_scoped_session
from beacon.services import domains as svc

router = APIRouter(prefix="/domains", tags=["domains"])


class DomainCreate(BaseModel):
    domain: str = Field(..., pattern=r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$")


class DomainOut(BaseModel):
    id: str
    domain: str
    verified: bool
    spf_status: str
    dmarc_status: str
    reputation_score: int
    created_at: datetime
    verified_at: datetime | None
    dns_instructions: list[dict] | None = None


def _require_org(request: Request) -> str:
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_required")
    return org_id


def _to_out(row, include_instructions: bool) -> DomainOut:
    out = DomainOut(
        id=row.id,
        domain=row.domain,
        verified=row.verified,
        spf_status=row.spf_status,
        dmarc_status=row.dmarc_status,
        reputation_score=row.reputation_score,
        created_at=row.created_at,
        verified_at=row.verified_at,
    )
    if include_instructions:
        out.dns_instructions = svc.domain_dns_instructions(row)["records"]
    return out


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DomainOut)
async def create_domain(payload: DomainCreate, request: Request) -> DomainOut:
    org_id = _require_org(request)
    async with tenant_scoped_session(org_id) as session:
        row = await svc.create_domain(session, organization_id=org_id, domain=payload.domain)
        return _to_out(row, include_instructions=True)


@router.get("", response_model=list[DomainOut])
async def list_domains(request: Request) -> list[DomainOut]:
    org_id = _require_org(request)
    async with tenant_scoped_session(org_id) as session:
        rows = await svc.list_domains(session, org_id)
    return [_to_out(r, include_instructions=False) for r in rows]


@router.post("/{domain_id}/verify", response_model=DomainOut)
async def verify_domain(domain_id: str, request: Request) -> DomainOut:
    org_id = _require_org(request)
    async with tenant_scoped_session(org_id) as session:
        try:
            row = await svc.verify_domain(session, org_id, domain_id)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
    return _to_out(row, include_instructions=False)

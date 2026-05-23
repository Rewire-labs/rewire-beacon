"""Endpoints `POST/GET/DELETE /v1/api-tokens`.

Auth scopes:
- POST   requires `api_tokens:write` (or org admin role inferred from JWT).
- GET    requires `api_tokens:read`.
- DELETE requires `api_tokens:write`.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from beacon.db.session import tenant_scoped_session
from beacon.services import api_tokens as svc

router = APIRouter(prefix="/api-tokens", tags=["api-tokens"])


class TokenCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    scopes: list[str] = Field(default_factory=lambda: ["messages:write"])
    expires_at: datetime | None = None


class TokenCreated(BaseModel):
    id: str
    name: str
    token: str  # plaintext — only on creation
    token_prefix: str
    scopes: list[str]
    expires_at: datetime | None
    created_at: datetime


class TokenSummary(BaseModel):
    id: str
    name: str
    token_prefix: str
    scopes: list[str]
    last_used_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


def _require_org(request: Request) -> str:
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_required")
    return org_id


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TokenCreated)
async def create_token(payload: TokenCreate, request: Request) -> TokenCreated:
    org_id = _require_org(request)
    user_id = None
    principal = getattr(request.state, "principal", None)
    if principal and principal.kind == "jwt":
        user_id = principal.subject
    async with tenant_scoped_session(org_id) as session:
        created = await svc.create_api_token(
            session,
            organization_id=org_id,
            name=payload.name,
            scopes=payload.scopes,
            expires_at=payload.expires_at,
            created_by_user_id=user_id,
        )
    return TokenCreated(**created)


@router.get("", response_model=list[TokenSummary])
async def list_tokens(request: Request) -> list[TokenSummary]:
    org_id = _require_org(request)
    async with tenant_scoped_session(org_id) as session:
        rows = await svc.list_api_tokens(session, org_id)
    return [
        TokenSummary(
            id=r.id,
            name=r.name,
            token_prefix=r.token_prefix,
            scopes=list(r.scopes),
            last_used_at=r.last_used_at,
            expires_at=r.expires_at,
            revoked_at=r.revoked_at,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_token(token_id: str, request: Request) -> None:
    org_id = _require_org(request)
    async with tenant_scoped_session(org_id) as session:
        ok = await svc.revoke_api_token(session, token_id, org_id)
    if not ok:
        raise HTTPException(status_code=404, detail="token_not_found")

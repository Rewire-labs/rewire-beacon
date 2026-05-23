"""Hot-path message send endpoints (`/v1/messages/*`).

Per BCN-024, BCN-053, BCN-063, BCN-082.
"""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from beacon.db.session import tenant_scoped_session
from beacon.services.messaging import (
    EmailMessageRequest,
    InvalidSenderError,
    QuotaExceededError,
    SuppressedError,
    enqueue_email,
)

router = APIRouter(prefix="/messages", tags=["messages"])


ConsentBasis = Literal["consent", "contract", "legal_obligation", "legitimate_interest"]


class EmailSendBody(BaseModel):
    sender: EmailStr
    to: list[EmailStr] = Field(..., min_length=1, max_length=50)
    subject: str = Field(..., min_length=1, max_length=512)
    html_body: str | None = None
    plain_body: str | None = None
    template_slug: str | None = Field(None, max_length=128)
    consent_basis: ConsentBasis
    metadata: dict[str, str] | None = None


class EmailSendResponse(BaseModel):
    message_id: str
    status: str
    chain_hash: str
    provider_route: str


def _require_org(request: Request) -> str:
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_required")
    return org_id


@router.post("/email", status_code=status.HTTP_202_ACCEPTED, response_model=EmailSendResponse)
async def send_email(payload: EmailSendBody, request: Request) -> EmailSendResponse:
    org_id = _require_org(request)
    req = EmailMessageRequest(
        sender=payload.sender,
        to=[str(a) for a in payload.to],
        subject=payload.subject,
        html_body=payload.html_body,
        plain_body=payload.plain_body,
        template_slug=payload.template_slug,
        consent_basis=payload.consent_basis,
        metadata=payload.metadata,
    )
    try:
        async with tenant_scoped_session(org_id) as session:
            result = await enqueue_email(session, organization_id=org_id, req=req)
    except SuppressedError as exc:
        raise HTTPException(status_code=409, detail={"error": "suppressed", "message": str(exc)})
    except InvalidSenderError as exc:
        raise HTTPException(status_code=422, detail={"error": "invalid_sender", "message": str(exc)})
    except QuotaExceededError as exc:
        raise HTTPException(status_code=402, detail={"error": "quota_exceeded", "message": str(exc)})
    return EmailSendResponse(
        message_id=result.message_id,
        status=result.status,
        chain_hash=result.chain_hash,
        provider_route=result.provider_route,
    )

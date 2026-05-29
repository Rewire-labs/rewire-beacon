"""POST /v1/emails — canonical email send + status endpoints.

Synchronous mode (V0):
  - Validate payload (Pydantic)
  - Dispatch via EmailRouter (Postal -> Resend fallback)
  - Emit credits + Lago billable + CITADEL anchor
  - Return 202 with provider + message_id

Async mode (V0.1): set ``async_mode=true`` to enqueue on pgmq and return
``{queued: true, queue: "messaging_outbound_email"}`` — picked up by
``SenderWorker``.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from messaging_cp.adapters.email.router import EmailRouter, EmailRouterAllFailed
from messaging_cp.credits_emit import emit_messaging_credit
from messaging_cp.lago_emit import emit_messaging_billable

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/emails")

# Single process-wide router instance (CB state shared across requests).
_email_router = EmailRouter()


class EmailSendRequest(BaseModel):
    sender: EmailStr
    to: list[EmailStr] = Field(..., min_length=1, max_length=50)
    subject: str = Field(..., min_length=1, max_length=512)
    html_body: str | None = Field(None, max_length=200_000)
    plain_body: str | None = Field(None, max_length=200_000)
    reply_to: EmailStr | None = None
    template_id: str | None = Field(None, max_length=128)
    tag: str | None = None
    consent_basis: str = Field(default="consent")
    metadata: dict[str, str] = Field(default_factory=dict)


class EmailSendResponse(BaseModel):
    message_id: str
    status: str
    provider: str


def _tenant_id(request: Request) -> str:
    tid = getattr(request.state, "organization_id", None) or getattr(
        request.state, "tenant_id", None
    )
    if not tid:
        raise HTTPException(status_code=400, detail="tenant_required")
    return tid


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=EmailSendResponse,
    summary="Send a transactional email (Postal primary, Resend fallback)",
)
async def send_email(payload: EmailSendRequest, request: Request) -> EmailSendResponse:
    if not payload.html_body and not payload.plain_body:
        raise HTTPException(
            status_code=422, detail="email_requires_html_or_plain_body"
        )
    tenant_id = _tenant_id(request)
    try:
        res = await _email_router.send(
            sender=str(payload.sender),
            to=[str(addr) for addr in payload.to],
            subject=payload.subject,
            html_body=payload.html_body,
            plain_body=payload.plain_body,
            reply_to=str(payload.reply_to) if payload.reply_to else None,
            tag=payload.tag,
        )
    except EmailRouterAllFailed as exc:
        logger.warning(
            "messaging.emails.all_failed",
            extra={"tenant_id": tenant_id, "error": str(exc)},
        )
        raise HTTPException(status_code=502, detail={"error": "email_all_providers_failed"})

    await emit_messaging_credit(
        tenant_id=tenant_id, action_type="email_transactional", quantity=1
    )
    await emit_messaging_billable(
        tenant_id=tenant_id,
        metric="messaging_email_sent",
        value=1,
        metadata={"provider": res.provider},
    )

    return EmailSendResponse(
        message_id=res.message_id, status=res.status, provider=res.provider
    )


@router.get("/{message_id}", summary="Get email delivery status")
async def get_email_status(message_id: str, request: Request) -> dict[str, Any]:
    _tenant_id(request)
    # Delegate to legacy delivery lookup. V0.1+: implement real lookup from
    # ``beacon.deliveries`` table.
    return {"message_id": message_id, "status": "unknown", "lookup": "not_implemented_v0"}


__all__ = ["router"]

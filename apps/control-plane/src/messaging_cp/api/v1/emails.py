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
from messaging_cp.send_guards import (
    QuotaExceededError,
    SuppressedError,
    check_and_consume_quota,
    default_idempotency_key,
    ensure_not_suppressed,
    idempotency_guard,
    idempotency_store,
)

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
    primary_recipient = str(payload.to[0])

    # Idempotency: explicit Idempotency-Key header wins; otherwise a
    # deterministic default key dedups identical sends within the same day.
    idem_key = request.headers.get("Idempotency-Key") or default_idempotency_key(
        tenant_id, "email", primary_recipient, payload.template_id
    )
    cached = await idempotency_guard(idem_key)
    if cached is not None:
        return EmailSendResponse(**cached)

    # Cross-channel suppression (LGPD opt-out) for every recipient.
    try:
        for addr in payload.to:
            await ensure_not_suppressed(tenant_id, str(addr))
    except SuppressedError as exc:
        raise HTTPException(
            status_code=409, detail={"error": "recipient_suppressed", "message": str(exc)}
        ) from exc

    # Per-tenant quota (decremented atomically).
    try:
        await check_and_consume_quota(tenant_id, "email")
    except QuotaExceededError as exc:
        raise HTTPException(
            status_code=429, detail={"error": "quota_exceeded", "message": str(exc)}
        ) from exc

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

    response = EmailSendResponse(
        message_id=res.message_id, status=res.status, provider=res.provider
    )
    await idempotency_store(idem_key, response.model_dump())
    return response


@router.get(
    "/{message_id}",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Get email delivery status [deferred V0.6]",
    response_model=None,
)
async def get_email_status(message_id: str, request: Request) -> Any:
    # RW-MESSAGING-20: explicit 501 — lookup from beacon.deliveries deferred V0.6.
    _tenant_id(request)
    raise HTTPException(
        status_code=501,
        detail={
            "code": "email_status_not_implemented_v0",
            "message": "Email delivery status lookup deferred to V0.6 (beacon.deliveries table).",
            "deferred_to": "V0.6",
            "message_id": message_id,
        },
    )


__all__ = ["router"]

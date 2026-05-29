"""Hot-path message send endpoints (`/v1/messages/*`).

Per BCN-024, BCN-053, BCN-063, BCN-082.
"""
from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from beacon.db.session import tenant_scoped_session
from beacon.services.messaging import (
    BlockedBySpamError,
    EmailMessageRequest,
    InvalidSenderError,
    PushMessageRequest,
    QuotaExceededError,
    SmsMessageRequest,
    SuppressedError,
    WhatsAppMessageRequest,
    enqueue_email,
    enqueue_push,
    enqueue_sms,
    enqueue_whatsapp,
)

# BUCKET 3 GAP-4 — IdempotencyMiddleware sentinel decorator.
try:
    from rewire_shared.http_client.idempotency import idempotent_required
except Exception:  # pragma: no cover - older rewire-shared
    def idempotent_required(func):  # type: ignore[misc]
        return func

_log = logging.getLogger(__name__)
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
@idempotent_required
async def send_email(payload: EmailSendBody, request: Request) -> EmailSendResponse:
    org_id = _require_org(request)
    _log.info("messaging.email.send", extra={"org_id": org_id, "sender": payload.sender, "recipients": len(payload.to)})
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
    except BlockedBySpamError as exc:
        raise HTTPException(status_code=451, detail={"error": "blocked_antispam", "message": str(exc)})
    return EmailSendResponse(
        message_id=result.message_id,
        status=result.status,
        chain_hash=result.chain_hash,
        provider_route=result.provider_route,
    )


# ---------- SMS ----------

E164 = Field(..., pattern=r"^\+[1-9]\d{6,14}$", description="E.164 phone")


class SmsSendBody(BaseModel):
    to: str = Field(..., pattern=r"^\+[1-9]\d{6,14}$")
    text: str = Field(..., min_length=1, max_length=918)  # 6 GSM-7 segments
    from_number: str | None = Field(None, max_length=20)
    template_slug: str | None = Field(None, max_length=128)
    consent_basis: ConsentBasis
    metadata: dict[str, str] | None = None


class GenericSendResponse(BaseModel):
    message_id: str
    status: str
    chain_hash: str
    provider_route: str


@router.post("/sms", status_code=status.HTTP_202_ACCEPTED, response_model=GenericSendResponse)
@idempotent_required
async def send_sms(payload: SmsSendBody, request: Request) -> GenericSendResponse:
    org_id = _require_org(request)
    _log.info("messaging.sms.send", extra={"org_id": org_id, "to": payload.to})
    req = SmsMessageRequest(
        to=payload.to,
        text=payload.text,
        from_number=payload.from_number,
        template_slug=payload.template_slug,
        consent_basis=payload.consent_basis,
        metadata=payload.metadata,
    )
    try:
        async with tenant_scoped_session(org_id) as session:
            r = await enqueue_sms(session, organization_id=org_id, req=req)
    except SuppressedError as exc:
        raise HTTPException(status_code=409, detail={"error": "suppressed", "message": str(exc)})
    except InvalidSenderError as exc:
        raise HTTPException(status_code=422, detail={"error": "invalid_sender", "message": str(exc)})
    except QuotaExceededError as exc:
        raise HTTPException(status_code=402, detail={"error": "quota_exceeded", "message": str(exc)})
    return GenericSendResponse(
        message_id=r.message_id, status=r.status,
        chain_hash=r.chain_hash, provider_route=r.provider_route,
    )


# ---------- Push (iOS/Android/Web unified entry) ----------

PushPlatform = Literal["ios", "android", "web"]


class PushSendBody(BaseModel):
    device_token: str = Field(..., min_length=8, max_length=512)
    title: str = Field(..., min_length=1, max_length=256)
    body: str = Field(..., min_length=1, max_length=1024)
    platform: PushPlatform
    data: dict[str, Any] | None = None
    push_app_id: str | None = None
    consent_basis: ConsentBasis


@router.post("/push", status_code=status.HTTP_202_ACCEPTED, response_model=GenericSendResponse)
@idempotent_required
async def send_push(payload: PushSendBody, request: Request) -> GenericSendResponse:
    org_id = _require_org(request)
    _log.info("messaging.push.send", extra={"org_id": org_id, "platform": payload.platform})
    req = PushMessageRequest(
        device_token=payload.device_token,
        title=payload.title,
        body=payload.body,
        platform=payload.platform,
        data=payload.data,
        consent_basis=payload.consent_basis,
        push_app_id=payload.push_app_id,
    )
    try:
        async with tenant_scoped_session(org_id) as session:
            r = await enqueue_push(session, organization_id=org_id, req=req)
    except SuppressedError as exc:
        raise HTTPException(status_code=409, detail={"error": "suppressed", "message": str(exc)})
    except InvalidSenderError as exc:
        raise HTTPException(status_code=422, detail={"error": "invalid_sender", "message": str(exc)})
    except QuotaExceededError as exc:
        raise HTTPException(status_code=402, detail={"error": "quota_exceeded", "message": str(exc)})
    return GenericSendResponse(
        message_id=r.message_id, status=r.status,
        chain_hash=r.chain_hash, provider_route=r.provider_route,
    )


# ---------- WhatsApp (via CONNECT) ----------


class WhatsAppSendBody(BaseModel):
    to: str = Field(..., pattern=r"^\+[1-9]\d{6,14}$")
    template_name: str = Field(..., min_length=1, max_length=128)
    template_vars: dict[str, Any] | None = None
    body_text: str | None = Field(None, max_length=4096)  # for in-session
    consent_basis: ConsentBasis


@router.post("/whatsapp", status_code=status.HTTP_202_ACCEPTED, response_model=GenericSendResponse)
@idempotent_required
async def send_whatsapp(payload: WhatsAppSendBody, request: Request) -> GenericSendResponse:
    org_id = _require_org(request)
    _log.info("messaging.whatsapp.send", extra={"org_id": org_id, "to": payload.to, "template": payload.template_name})
    req = WhatsAppMessageRequest(
        to=payload.to,
        template_name=payload.template_name,
        template_vars=payload.template_vars,
        body_text=payload.body_text,
        consent_basis=payload.consent_basis,
    )
    try:
        async with tenant_scoped_session(org_id) as session:
            r = await enqueue_whatsapp(session, organization_id=org_id, req=req)
    except SuppressedError as exc:
        raise HTTPException(status_code=409, detail={"error": "suppressed", "message": str(exc)})
    except InvalidSenderError as exc:
        raise HTTPException(status_code=422, detail={"error": "invalid_sender", "message": str(exc)})
    except QuotaExceededError as exc:
        raise HTTPException(status_code=402, detail={"error": "quota_exceeded", "message": str(exc)})
    return GenericSendResponse(
        message_id=r.message_id, status=r.status,
        chain_hash=r.chain_hash, provider_route=r.provider_route,
    )

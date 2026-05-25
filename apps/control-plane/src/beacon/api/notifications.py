"""Notifications dispatcher endpoint — umbrella entry point for multi-canal sends.

Lote 8 (rewire-messaging): consolidação notify+beacon. Cliente bate
`POST /v1/notifications` informando channel e o dispatcher delega para o
hot-path correto (`enqueue_email`, `enqueue_sms`, `enqueue_push`,
`enqueue_whatsapp`) com validação Pydantic discriminada.

`GET /v1/channels` retorna o catálogo de canais disponíveis para o tenant.
V0: catálogo estático (sem per-tenant override). V0.2: per-tenant via
`beacon.channels` table.
"""
from __future__ import annotations

from typing import Annotated, Literal

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

router = APIRouter()

Channel = Literal["email", "sms", "whatsapp", "push_mobile", "push_web"]
ConsentBasis = Literal["consent", "contract", "legal_obligation", "legitimate_interest"]


class NotificationCreate(BaseModel):
    """Umbrella request — campos opcionais validados conforme channel."""

    channel: Channel
    recipient: str = Field(..., min_length=1, max_length=512)
    template_id: str | None = Field(None, max_length=128)
    body: str | None = Field(None, max_length=8192)
    subject: str | None = Field(None, max_length=512)
    sender: EmailStr | None = None
    consent_basis: ConsentBasis = "consent"
    metadata: dict[str, str] = Field(default_factory=dict)
    # push-specific
    push_title: str | None = Field(None, max_length=256)
    push_app_id: str | None = None
    # whatsapp-specific
    template_vars: dict[str, str] | None = None


class NotificationAccepted(BaseModel):
    notification_id: str
    status: str
    channel: str
    chain_hash: str
    provider_route: str


def _require_org(request: Request) -> str:
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_required")
    return org_id


def _map_messaging_error(exc: Exception) -> HTTPException:
    """Convert services.messaging exceptions to HTTP errors RFC 7807 style."""
    if isinstance(exc, SuppressedError):
        return HTTPException(status_code=409, detail={"error": "suppressed", "message": str(exc)})
    if isinstance(exc, InvalidSenderError):
        return HTTPException(status_code=422, detail={"error": "invalid_sender", "message": str(exc)})
    if isinstance(exc, QuotaExceededError):
        return HTTPException(status_code=402, detail={"error": "quota_exceeded", "message": str(exc)})
    if isinstance(exc, BlockedBySpamError):
        return HTTPException(status_code=451, detail={"error": "blocked_antispam", "message": str(exc)})
    return HTTPException(status_code=500, detail={"error": "internal_error", "message": str(exc)})


@router.post(
    "/notifications",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=NotificationAccepted,
    summary="Dispatch a multi-canal notification",
)
async def send_notification(
    payload: NotificationCreate, request: Request
) -> NotificationAccepted:
    """Dispatcher umbrella — delega ao canal correto."""
    org_id = _require_org(request)

    try:
        async with tenant_scoped_session(org_id) as session:
            if payload.channel == "email":
                if not payload.sender or not payload.subject:
                    raise HTTPException(
                        status_code=422,
                        detail={
                            "error": "missing_fields",
                            "message": "email requires sender + subject",
                        },
                    )
                req_email = EmailMessageRequest(
                    sender=payload.sender,
                    to=[payload.recipient],
                    subject=payload.subject,
                    html_body=payload.body,
                    plain_body=None,
                    template_slug=payload.template_id,
                    consent_basis=payload.consent_basis,
                    metadata=payload.metadata,
                )
                result = await enqueue_email(session, organization_id=org_id, req=req_email)
            elif payload.channel == "sms":
                req_sms = SmsMessageRequest(
                    to=payload.recipient,
                    text=payload.body or "",
                    from_number=None,
                    template_slug=payload.template_id,
                    consent_basis=payload.consent_basis,
                    metadata=payload.metadata,
                )
                result = await enqueue_sms(session, organization_id=org_id, req=req_sms)
            elif payload.channel in ("push_mobile", "push_web"):
                platform = "web" if payload.channel == "push_web" else "ios"
                req_push = PushMessageRequest(
                    device_token=payload.recipient,
                    title=payload.push_title or "Notificação",
                    body=payload.body or "",
                    platform=platform,
                    data=None,
                    consent_basis=payload.consent_basis,
                    push_app_id=payload.push_app_id,
                )
                result = await enqueue_push(session, organization_id=org_id, req=req_push)
            elif payload.channel == "whatsapp":
                req_wa = WhatsAppMessageRequest(
                    to=payload.recipient,
                    template_name=payload.template_id or "default",
                    template_vars=payload.template_vars,
                    body_text=payload.body,
                    consent_basis=payload.consent_basis,
                )
                result = await enqueue_whatsapp(session, organization_id=org_id, req=req_wa)
            else:
                raise HTTPException(status_code=422, detail=f"unsupported_channel: {payload.channel}")
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise _map_messaging_error(exc)

    return NotificationAccepted(
        notification_id=result.message_id,
        status=result.status,
        channel=payload.channel,
        chain_hash=result.chain_hash,
        provider_route=result.provider_route,
    )


@router.get("/channels", summary="List available channels for the calling tenant")
async def list_channels(request: Request) -> dict[str, object]:
    """V0: catálogo estático multi-canal. V0.2: per-tenant via beacon.channels."""
    org_id = getattr(request.state, "organization_id", None)
    return {
        "organization_id": org_id,
        "channels": [
            {"id": "email", "enabled": True, "provider": "postal+ses-br+resend"},
            {"id": "sms", "enabled": True, "provider": "zenvia+totalvoice"},
            {"id": "whatsapp", "enabled": True, "provider": "connect-internal"},
            {"id": "push_mobile", "enabled": True, "provider": "apns+fcm"},
            {"id": "push_web", "enabled": True, "provider": "vapid"},
        ],
    }

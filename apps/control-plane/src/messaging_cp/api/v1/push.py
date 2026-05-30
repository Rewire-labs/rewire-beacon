"""POST /v1/push — push notifications (APNs/FCM) + device-token registration."""

from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from messaging_cp.adapters.push.router import (
    PushRouter,
    PushRouterCircuitOpen,
    PushRouterError,
)
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

router = APIRouter(prefix="/v1/push")
_push_router = PushRouter()


class PushSendRequest(BaseModel):
    device_token: str = Field(..., min_length=8, max_length=4096)
    platform: Literal["ios", "android", "web"]
    title: str = Field(..., max_length=256)
    body: str = Field(..., max_length=1024)
    data: dict[str, str] | None = None
    consent_basis: str = Field(default="consent")
    push_app_id: str | None = None


class PushSendResponse(BaseModel):
    message_id: str
    status: str
    provider: str
    platform: str


class DeviceTokenRegister(BaseModel):
    device_token: str = Field(..., min_length=8, max_length=4096)
    platform: Literal["ios", "android", "web"]
    user_id: str | None = None
    push_app_id: str | None = None
    locale: str | None = "pt-BR"


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
    response_model=PushSendResponse,
    summary="Send a push notification (APNs/FCM/VAPID)",
)
async def send_push(payload: PushSendRequest, request: Request) -> PushSendResponse:
    tenant_id = _tenant_id(request)

    idem_key = request.headers.get("Idempotency-Key") or default_idempotency_key(
        tenant_id, "push", payload.device_token, payload.push_app_id
    )
    cached = await idempotency_guard(idem_key)
    if cached is not None:
        return PushSendResponse(**cached)

    try:
        await ensure_not_suppressed(tenant_id, payload.device_token)
    except SuppressedError as exc:
        raise HTTPException(
            status_code=409, detail={"error": "recipient_suppressed", "message": str(exc)}
        ) from exc
    try:
        await check_and_consume_quota(tenant_id, "push")
    except QuotaExceededError as exc:
        raise HTTPException(
            status_code=429, detail={"error": "quota_exceeded", "message": str(exc)}
        ) from exc

    try:
        res = await _push_router.send(
            platform=payload.platform,
            device_token=payload.device_token,
            title=payload.title,
            body=payload.body,
            data=payload.data,
        )
    except PushRouterCircuitOpen as exc:
        raise HTTPException(status_code=503, detail={"error": "push_circuit_open", "message": str(exc)})
    except PushRouterError as exc:
        logger.warning(
            "messaging.push.failed",
            extra={"tenant_id": tenant_id, "platform": payload.platform, "error": str(exc)},
        )
        raise HTTPException(status_code=502, detail={"error": "push_send_failed", "message": str(exc)})
    except NotImplementedError as exc:
        # CORR-2 sweep (2026-05-26): zero 501 binário. NotImplementedError lançado
        # por adapter web push pendente em V0.3 = 410 Gone (deferred), com Link
        # successor-version apontando para roadmap doc + Sunset header (RFC 8594).
        raise HTTPException(
            status_code=410,
            headers={
                "Sunset": "Sat, 31 Dec 2026 23:59:59 GMT",
                "Link": '</docs/products/messaging/ROADMAP.md#web-push-v0-3>; rel="successor-version"',
                "X-Rewire-Deprecated": "true",
            },
            detail={
                "code": "platform_web_push_deferred_v0_3",
                "message": str(exc) or "Web push (VAPID) deferred to V0.3 — use platform=apns or platform=fcm in V0.",
                "successor": "platform=apns or platform=fcm",
            },
        )

    await emit_messaging_credit(tenant_id=tenant_id, action_type="push_notification", quantity=1)
    await emit_messaging_billable(
        tenant_id=tenant_id,
        metric="messaging_push_sent",
        value=1,
        metadata={"provider": res.provider, "platform": res.platform},
    )

    response = PushSendResponse(
        message_id=res.message_id,
        status=res.status,
        provider=res.provider,
        platform=res.platform,
    )
    await idempotency_store(idem_key, response.model_dump())
    return response


@router.get(
    "/{message_id}",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Get push delivery status [deferred V0.6]",
    response_model=None,
)
async def get_push_status(message_id: str, request: Request) -> Any:
    # RW-MESSAGING-20: explicit 501 — lookup from beacon.deliveries deferred V0.6.
    _tenant_id(request)
    raise HTTPException(
        status_code=501,
        detail={
            "code": "push_status_not_implemented_v0",
            "message": "Push delivery status lookup deferred to V0.6 (beacon.deliveries table).",
            "deferred_to": "V0.6",
            "message_id": message_id,
        },
    )


@router.post(
    "/devices",
    status_code=status.HTTP_201_CREATED,
    summary="Register a device token for a tenant user",
)
async def register_device(payload: DeviceTokenRegister, request: Request) -> dict[str, Any]:
    tenant_id = _tenant_id(request)
    # V0: stub registration; V0.1 inserts into beacon.devices table with
    # RLS FORCE policy. Returns echo response.
    logger.info(
        "messaging.push.device_register",
        extra={
            "tenant_id": tenant_id,
            "platform": payload.platform,
            "user_id": payload.user_id,
        },
    )
    return {
        "registered": True,
        "tenant_id": tenant_id,
        "platform": payload.platform,
        "device_token_hint": payload.device_token[:6] + "...",
    }


__all__ = ["router"]

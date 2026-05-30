"""POST /v1/sms — canonical SMS send endpoints (Zenvia BR primary)."""

from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from messaging_cp.adapters.sms.router import SmsRouter, SmsRouterAllFailed
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

router = APIRouter(prefix="/v1/sms")
_sms_router = SmsRouter()

# E.164-ish for BR (+55 + DDD + 8-9 digits).
_BR_E164 = re.compile(r"^\+55\d{10,11}$")


class SmsSendRequest(BaseModel):
    to: str = Field(..., description="E.164 BR phone, e.g. +5511999998888")
    text: str = Field(..., min_length=1, max_length=480)
    from_number: str | None = None
    template_id: str | None = None
    consent_basis: str = Field(default="consent")
    metadata: dict[str, str] = Field(default_factory=dict)


class SmsSendResponse(BaseModel):
    message_id: str
    status: str
    provider: str
    cost_brl_cents: int


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
    response_model=SmsSendResponse,
    summary="Send a transactional SMS (BR — Zenvia)",
)
async def send_sms(payload: SmsSendRequest, request: Request) -> SmsSendResponse:
    if not _BR_E164.match(payload.to):
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_recipient", "message": "phone must be E.164 BR (+55...)"},
        )
    tenant_id = _tenant_id(request)

    idem_key = request.headers.get("Idempotency-Key") or default_idempotency_key(
        tenant_id, "sms", payload.to, payload.template_id
    )
    cached = await idempotency_guard(idem_key)
    if cached is not None:
        return SmsSendResponse(**cached)

    try:
        await ensure_not_suppressed(tenant_id, payload.to)
    except SuppressedError as exc:
        raise HTTPException(
            status_code=409, detail={"error": "recipient_suppressed", "message": str(exc)}
        ) from exc
    try:
        await check_and_consume_quota(tenant_id, "sms")
    except QuotaExceededError as exc:
        raise HTTPException(
            status_code=429, detail={"error": "quota_exceeded", "message": str(exc)}
        ) from exc

    try:
        res = await _sms_router.send(
            from_number=payload.from_number or "Rewire",
            to=payload.to,
            text=payload.text,
        )
    except SmsRouterAllFailed as exc:
        logger.warning(
            "messaging.sms.all_failed", extra={"tenant_id": tenant_id, "error": str(exc)}
        )
        raise HTTPException(status_code=502, detail={"error": "sms_all_providers_failed"})

    await emit_messaging_credit(tenant_id=tenant_id, action_type="sms_br", quantity=1)
    await emit_messaging_billable(
        tenant_id=tenant_id,
        metric="messaging_sms_sent",
        value=1,
        metadata={"provider": res.provider, "cost_brl_cents": res.cost_brl_cents},
    )

    response = SmsSendResponse(
        message_id=res.message_id,
        status=res.status,
        provider=res.provider,
        cost_brl_cents=res.cost_brl_cents,
    )
    await idempotency_store(idem_key, response.model_dump())
    return response


@router.get(
    "/{message_id}",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Get SMS delivery status [deferred V0.6]",
    response_model=None,
)
async def get_sms_status(message_id: str, request: Request) -> Any:
    # RW-MESSAGING-20: explicit 501 — lookup from beacon.deliveries deferred V0.6.
    _tenant_id(request)
    raise HTTPException(
        status_code=501,
        detail={
            "code": "sms_status_not_implemented_v0",
            "message": "SMS delivery status lookup deferred to V0.6 (beacon.deliveries table).",
            "deferred_to": "V0.6",
            "message_id": message_id,
        },
    )


__all__ = ["router"]

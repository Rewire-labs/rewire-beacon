# notifications router
"""Compose-and-send notification router (FE-MESSAGING-04).

Backs the beacon-ui compose screen: accepts a channel + recipient +
content/template and runs the canonical MessagingService choke-point
(suppression / idempotency / preferences / rate-limit / freq-cap / quota)
before reporting the decision.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from beacon.services.messaging import (
    Channel,
    MessagingService,
    SendDecision,
    SendRequest,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])

# Process-local service; production injects DB/Redis-backed stores.
_service = MessagingService()


class SendPayload(BaseModel):
    channel: str = Field(..., description="email|sms|push|whatsapp")
    recipient: str
    category: str = "transactional"
    subject: str = ""
    body: str = ""
    template_id: str | None = None
    idempotency_key: str | None = None


class SendResponse(BaseModel):
    decision: str
    reason: str
    accepted: bool


class ChannelInfo(BaseModel):
    id: str
    enabled: bool
    provider: str


class ChannelsResponse(BaseModel):
    organization_id: str | None = None
    channels: list[ChannelInfo]


@router.get("/channels", response_model=ChannelsResponse)
def list_channels() -> ChannelsResponse:
    """FE-MESSAGING-08: list enabled channels for the org."""
    return ChannelsResponse(
        channels=[
            ChannelInfo(id="email", enabled=True, provider="postal+ses-br+resend"),
            ChannelInfo(id="sms", enabled=True, provider="zenvia+totalvoice"),
            ChannelInfo(id="whatsapp", enabled=True, provider="connect-internal"),
            ChannelInfo(id="push_mobile", enabled=True, provider="apns+fcm"),
            ChannelInfo(id="push_web", enabled=False, provider="vapid"),
        ]
    )


@router.post("/send", response_model=SendResponse)
def send_notification(payload: SendPayload) -> SendResponse:
    try:
        channel = Channel(payload.channel)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"invalid channel: {payload.channel}") from exc

    if not payload.body and not payload.template_id:
        raise HTTPException(status_code=422, detail="body or template_id required")

    req = SendRequest(
        tenant_id="current",  # resolved from auth context in production
        channel=channel,
        recipient=payload.recipient,
        category=payload.category,
        idempotency_key=payload.idempotency_key,
        body=payload.body,
    )
    result = _service.evaluate(req)
    return SendResponse(
        decision=result.decision.value,
        reason=result.reason,
        accepted=result.decision is SendDecision.ALLOW,
    )

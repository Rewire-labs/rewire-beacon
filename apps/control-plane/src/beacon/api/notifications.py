"""V0 stub — send notification + list channels.

Spec: futuros_produtos.md secao 2.8/2.10 (BEACON API).
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

router = APIRouter()

Channel = Literal["email", "sms", "whatsapp", "push_mobile", "push_web"]


class NotificationCreate(BaseModel):
    """Request schema — V0 placeholder."""

    channel: Channel
    recipient: str = Field(..., description="email, E.164 phone, FCM token, etc")
    template_id: str | None = None
    body: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class NotificationAccepted(BaseModel):
    notification_id: str
    status: str
    todo: str | None = None


@router.post(
    "/notifications",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=NotificationAccepted,
    summary="Enqueue a notification for delivery (V0 STUB)",
)
async def send_notification(payload: NotificationCreate) -> NotificationAccepted:
    """V0 stub — no actual dispatch. V0.2 will enqueue to Kafka topic."""
    return NotificationAccepted(
        notification_id="ntf_v0_stub_0000000000",
        status="not_implemented",
        todo="V0.2 — wire Kafka producer + suppression check + audit chain anchor",
    )


@router.get(
    "/channels",
    summary="List available channels for the calling tenant (V0 STUB)",
)
async def list_channels() -> dict[str, object]:
    """V0 stub — returns canonical channel catalog."""
    return {
        "status": "not_implemented",
        "todo": "V0.2 — return tenant-configured channels + per-channel quota",
        "channels": [
            {"id": "email", "enabled": True, "provider": "postal+ses-br"},
            {"id": "sms", "enabled": False, "provider": "zenvia+totalvoice"},
            {"id": "whatsapp", "enabled": False, "provider": "connect-internal"},
            {"id": "push_mobile", "enabled": False, "provider": "apns+fcm"},
            {"id": "push_web", "enabled": False, "provider": "vapid"},
        ],
    }

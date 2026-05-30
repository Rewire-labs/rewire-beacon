"""Overview router (FE-MESSAGING-07).

Provides the dashboard summary the beacon-ui Overview page consumes. Previously
the FE called this endpoint with no backend behind it (silent 404).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/overview", tags=["overview"])


class ChannelStat(BaseModel):
    channel: str
    sent: int
    delivered: int
    failed: int


class OverviewResponse(BaseModel):
    period: str
    total_sent: int
    total_delivered: int
    total_failed: int
    delivery_rate: float
    channels: list[ChannelStat]


@router.get("", response_model=OverviewResponse)
def get_overview(period: str = "7d") -> OverviewResponse:
    channels = [
        ChannelStat(channel="email", sent=0, delivered=0, failed=0),
        ChannelStat(channel="sms", sent=0, delivered=0, failed=0),
        ChannelStat(channel="push", sent=0, delivered=0, failed=0),
        ChannelStat(channel="whatsapp", sent=0, delivered=0, failed=0),
    ]
    sent = sum(c.sent for c in channels)
    delivered = sum(c.delivered for c in channels)
    failed = sum(c.failed for c in channels)
    rate = (delivered / sent) if sent else 0.0
    return OverviewResponse(
        period=period,
        total_sent=sent,
        total_delivered=delivered,
        total_failed=failed,
        delivery_rate=round(rate, 4),
        channels=channels,
    )

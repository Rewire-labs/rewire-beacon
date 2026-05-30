"""Deliverability metrics router (FE-MESSAGING-07)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/deliverability", tags=["deliverability"])


class DeliverabilityResponse(BaseModel):
    bounce_rate: float
    complaint_rate: float
    open_rate: float
    click_rate: float
    reputation_score: float


@router.get("", response_model=DeliverabilityResponse)
def get_deliverability(period: str = "30d") -> DeliverabilityResponse:
    return DeliverabilityResponse(
        bounce_rate=0.0,
        complaint_rate=0.0,
        open_rate=0.0,
        click_rate=0.0,
        reputation_score=100.0,
    )

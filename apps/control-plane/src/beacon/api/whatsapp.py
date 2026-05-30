"""WhatsApp management endpoints (FE-MESSAGING-08).

- GET /v1/whatsapp/status     — connection status + quality rating
- GET /v1/whatsapp/templates  — approved template library
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


class WaStatus(BaseModel):
    connected: bool
    quality_rating: str  # "green" | "yellow" | "red" | "unknown"
    templates_synced: int


class WaTemplate(BaseModel):
    id: str
    name: str
    category: str  # "MARKETING" | "UTILITY" | "AUTHENTICATION"
    status: str    # "APPROVED" | "PENDING" | "REJECTED"
    language: str


@router.get("/status", response_model=WaStatus)
def get_status() -> WaStatus:
    """Return current WhatsApp Business API connection status."""
    return WaStatus(connected=False, quality_rating="unknown", templates_synced=0)


@router.get("/templates", response_model=list[WaTemplate])
def list_templates() -> list[WaTemplate]:
    """Return approved WhatsApp message templates for the tenant."""
    return []

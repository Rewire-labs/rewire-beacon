"""Outbound webhook management endpoints (FE-MESSAGING-09).

Tenant-registered outbound webhooks that Beacon calls when events occur
(e.g. message delivered, bounced, complained).

- GET    /v1/webhooks/endpoints          — list registered endpoints
- POST   /v1/webhooks/endpoints          — register a new endpoint
- DELETE /v1/webhooks/endpoints/{id}     — remove an endpoint
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, HttpUrl

router = APIRouter(prefix="/webhooks/endpoints", tags=["webhooks-mgmt"])


class WebhookEndpoint(BaseModel):
    id: str
    name: str
    url: str
    events: list[str]
    status: str  # "active" | "disabled"
    created_at: str | None = None


class WebhookCreate(BaseModel):
    name: str
    url: str
    events: list[str] = []
    secret: str | None = None


@router.get("", response_model=list[WebhookEndpoint])
def list_endpoints() -> list[WebhookEndpoint]:
    """V0 stub — returns empty list; V0.2 persists in DB."""
    return []


@router.post("", status_code=201, response_model=WebhookEndpoint)
def create_endpoint(payload: WebhookCreate) -> WebhookEndpoint:
    """V0 stub — acknowledges creation; V0.2 stores + verifies endpoint."""
    import uuid
    return WebhookEndpoint(
        id=str(uuid.uuid4()),
        name=payload.name,
        url=payload.url,
        events=payload.events,
        status="active",
    )


@router.delete("/{endpoint_id}", status_code=204)
def delete_endpoint(endpoint_id: str) -> None:
    """V0 stub — no-op; V0.2 deletes from DB."""
    return None

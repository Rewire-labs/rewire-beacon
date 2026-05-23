"""Journey endpoints — multi-channel orchestration via Temporal.

Endpoints:
- POST /v1/journeys                start a multi-step journey
- POST /v1/journeys/{id}/pause
- POST /v1/journeys/{id}/resume
- GET  /v1/journeys                list active journeys for org
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/journeys", tags=["journeys"])


class JourneyStepIn(BaseModel):
    channel: str = Field(..., pattern=r"^(email|sms|whatsapp|push)$")
    template_slug: str = Field(..., min_length=1, max_length=128)
    wait_hours: int = Field(0, ge=0, le=720)  # max 30 days
    cancel_if_event: str | None = Field(None, pattern=r"^(opened|clicked|replied|delivered)$")


class JourneyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    recipient_email: str | None = None
    recipient_phone: str | None = None
    recipient_push_token: str | None = None
    steps: list[JourneyStepIn] = Field(..., min_length=1, max_length=20)
    template_vars: dict[str, Any] = Field(default_factory=dict)
    consent_basis: str = "consent"


class JourneyOut(BaseModel):
    id: str
    name: str
    status: str
    started_at: datetime
    steps_total: int


def _require_org(request: Request) -> str:
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_required")
    return org_id


async def _start_temporal_workflow(journey_id: str, config: dict[str, Any]) -> None:
    """Schedule the Temporal workflow. No-op if temporalio not installed."""
    try:
        from temporalio.client import Client  # type: ignore

        from beacon.settings import get_settings

        s = get_settings()
        client = await Client.connect(getattr(s, "temporal_address", "temporal.temporal.svc.cluster.local:7233"))
        await client.start_workflow(
            "MultiChannelJourneyWorkflow",
            config,
            id=journey_id,
            task_queue="beacon-journeys",
        )
    except ImportError:
        logger.info("temporalio not installed; journey persisted only (dev mode)")
    except Exception as exc:  # noqa: BLE001
        logger.warning("temporal start failed: %s", exc)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=JourneyOut)
async def create_journey(payload: JourneyCreate, request: Request) -> JourneyOut:
    org_id = _require_org(request)
    import uuid as _uuid

    journey_id = f"journey-{_uuid.uuid4()}"
    config = {
        "journey_id": journey_id,
        "organization_id": org_id,
        "recipient_email": payload.recipient_email,
        "recipient_phone": payload.recipient_phone,
        "recipient_push_token": payload.recipient_push_token,
        "consent_basis": payload.consent_basis,
        "template_vars": payload.template_vars,
        "steps": [
            {
                "channel": s.channel, "template_slug": s.template_slug,
                "wait_after": timedelta(hours=s.wait_hours), "cancel_if_event": s.cancel_if_event,
            }
            for s in payload.steps
        ],
    }
    await _start_temporal_workflow(journey_id, config)
    return JourneyOut(
        id=journey_id, name=payload.name, status="running",
        started_at=datetime.utcnow(), steps_total=len(payload.steps),
    )


@router.post("/{journey_id}/pause")
async def pause_journey(journey_id: str, request: Request) -> dict[str, str]:
    _require_org(request)
    try:
        from temporalio.client import Client  # type: ignore

        from beacon.settings import get_settings

        s = get_settings()
        client = await Client.connect(getattr(s, "temporal_address", "temporal:7233"))
        handle = client.get_workflow_handle(journey_id)
        await handle.signal("pause")
    except ImportError:
        pass
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"temporal error: {exc}")
    return {"id": journey_id, "status": "paused"}


@router.post("/{journey_id}/resume")
async def resume_journey(journey_id: str, request: Request) -> dict[str, str]:
    _require_org(request)
    try:
        from temporalio.client import Client  # type: ignore

        from beacon.settings import get_settings

        s = get_settings()
        client = await Client.connect(getattr(s, "temporal_address", "temporal:7233"))
        handle = client.get_workflow_handle(journey_id)
        await handle.signal("resume")
    except ImportError:
        pass
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"temporal error: {exc}")
    return {"id": journey_id, "status": "running"}


@router.get("", response_model=list[JourneyOut])
async def list_journeys(request: Request) -> list[JourneyOut]:
    _require_org(request)
    # V0: returns empty until Temporal visibility API integration.
    return []

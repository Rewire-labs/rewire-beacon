"""V0 stub — delivery status lookup."""

from __future__ import annotations

from fastapi import APIRouter, Query

router = APIRouter()


@router.get(
    "/deliveries",
    summary="List recent deliveries with status (V0 STUB)",
)
async def list_deliveries(
    limit: int = Query(default=50, ge=1, le=500),
    channel: str | None = Query(default=None),
) -> dict[str, object]:
    """V0 stub — ClickHouse query planned for V0.3."""
    return {
        "status": "not_implemented",
        "todo": "V0.3 — ClickHouse query against beacon_events table",
        "limit": limit,
        "channel": channel,
        "items": [],
    }


@router.get(
    "/deliveries/{delivery_id}",
    summary="Fetch a single delivery with full status history (V0 STUB)",
)
async def get_delivery(delivery_id: str) -> dict[str, object]:
    return {
        "status": "not_implemented",
        "todo": "V0.3 — join across deliveries + events tables",
        "delivery_id": delivery_id,
    }

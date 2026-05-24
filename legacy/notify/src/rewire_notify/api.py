"""FastAPI route handlers (``/alerts/telegram``, ``/events``, health)."""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

from rewire_notify.dispatcher import (
    Dispatcher,
    alertmanager_payload_to_events,
    event_payload_to_event,
)
from rewire_notify.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


def _verify_hmac(secret: str, body: bytes, signature: str | None) -> bool:
    """Return True if the optional Alertmanager HMAC header matches.

    The signature is expected as ``sha256=<hex>`` (GitHub-style) so the
    helper is reusable for other webhook callers.
    """
    if not secret:
        # HMAC is opt-in — empty secret means "trust the ClusterIP".
        return True
    if not signature:
        return False
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


@router.post("/alerts/telegram")
async def alerts_telegram(
    request: Request,
    x_rewire_signature: str | None = Header(default=None),
) -> dict[str, Any]:
    """Alertmanager webhook → Telegram fan-out.

    Alertmanager batches alerts; we dispatch each one individually.
    """
    s = get_settings()
    body = await request.body()
    if not _verify_hmac(s.alertmanager_hmac_secret, body, x_rewire_signature):
        raise HTTPException(status_code=401, detail="invalid signature")
    try:
        payload = await request.json()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"invalid json: {exc}") from exc

    events = alertmanager_payload_to_events(payload)
    dispatcher: Dispatcher = request.app.state.dispatcher
    await dispatcher.dispatch_many(events)
    return {"status": "ok", "dispatched": len(events)}


@router.post("/events")
async def events_endpoint(request: Request) -> dict[str, Any]:
    """Direct event POST (used by producers without Redpanda).

    Body shape:
        ``{kind, severity, timestamp, tenant_id?, payload?}``
    """
    try:
        payload = await request.json()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"invalid json: {exc}") from exc
    if "kind" not in payload:
        raise HTTPException(status_code=400, detail="missing required field: kind")
    event = event_payload_to_event(payload)
    dispatcher: Dispatcher = request.app.state.dispatcher
    await dispatcher.dispatch(event)
    return {"status": "ok", "kind": event.kind}


@router.get("/healthz", include_in_schema=False)
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz", include_in_schema=False)
async def readyz(request: Request) -> dict[str, str]:
    # Liveness is enough for the bot — readiness checks the adapter pool.
    dispatcher = getattr(request.app.state, "dispatcher", None)
    if dispatcher is None:
        raise HTTPException(status_code=503, detail="dispatcher not ready")
    return {"status": "ok"}

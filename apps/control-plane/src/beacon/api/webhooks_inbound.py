"""Inbound webhook handlers from external providers.

Routes:
- POST /v1/webhooks/inbound/postal  — Postal bounce/complaint events.
- POST /v1/webhooks/inbound/ses     — AWS SES SNS notifications.
- POST /v1/webhooks/inbound/zenvia  — Zenvia SMS delivery status + 2-way.

All paths are public (no auth middleware) since they come from external
systems. Verification is via per-provider signing secret (HMAC verify).
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

from beacon.db.session import worker_session
from beacon.services import suppression as svc

router = APIRouter(prefix="/webhooks/inbound", tags=["webhooks-inbound"])
logger = logging.getLogger(__name__)


def _postal_secret() -> bytes:
    return os.environ.get("BEACON_POSTAL_WEBHOOK_SECRET", "dev-postal-secret").encode()


def _verify_postal_signature(body: bytes, signature: str | None) -> bool:
    if not signature:
        return os.environ.get("BEACON_ENV", "dev") == "dev"
    expected = hmac.new(_postal_secret(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


@router.post("/postal")
async def postal_inbound(
    request: Request,
    x_postal_signature: str | None = Header(None),
) -> dict[str, Any]:
    body = await request.body()
    if not _verify_postal_signature(body, x_postal_signature):
        raise HTTPException(status_code=401, detail="invalid_signature")
    import json

    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invalid_json")

    event_type = event.get("event", "unknown")
    payload = event.get("payload", {})
    org_id = (payload.get("server", {}) or {}).get("organization")
    if not org_id:
        # Postal sometimes nests in different shape — accept anyway, log.
        logger.warning("postal_event_no_org event=%s", event_type)
        return {"status": "accepted_no_org"}

    suppress_reason: str | None = None
    if event_type in ("MessageBounced", "MessageDeliveryFailed"):
        if (payload.get("bounce", {}) or {}).get("type") == "hard":
            suppress_reason = "hard_bounce"
    elif event_type == "MessageComplained":
        suppress_reason = "complaint"

    recipient = (
        payload.get("recipient")
        or (payload.get("message", {}) or {}).get("to")
        or (payload.get("output", {}) or {}).get("to")
    )

    if suppress_reason and recipient:
        async with worker_session() as session:
            await svc.add(
                session,
                organization_id=org_id,
                identifier_type="email",
                identifier_value=recipient,
                reason=suppress_reason,
                source_channel="email",
                notes=f"postal:{event_type}",
            )
        logger.info("postal.suppressed org=%s reason=%s recipient=%s", org_id, suppress_reason, recipient)
    return {"status": "processed", "event": event_type, "suppressed": bool(suppress_reason)}

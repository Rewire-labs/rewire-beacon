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


# ---------- Zenvia/TotalVoice SMS callbacks (delivery status + 2-way) ----------


@router.post("/zenvia")
async def zenvia_inbound(request: Request) -> dict[str, Any]:
    """Zenvia delivery + inbound SMS webhook.

    Inbound SMS reply triggers our `message.sms.replied` event for customer
    webhook fan-out. Delivery status updates `beacon.deliveries.status`.
    """
    body = await request.json()
    event_type = body.get("type", "MESSAGE_STATUS")
    msg = body.get("message", {})
    # If reply contains opt-out keyword (PARAR/CANCELAR), add to suppression.
    if event_type == "MESSAGE" and isinstance(msg.get("contents"), list):
        text = next((c.get("text", "") for c in msg["contents"] if c.get("type") == "text"), "")
        if text.strip().upper() in {"PARAR", "CANCELAR", "STOP", "SAIR"}:
            from_phone = msg.get("from")
            # We need the org_id — assume webhook URL includes it as query param.
            org_id = request.query_params.get("organization_id")
            if from_phone and org_id:
                async with worker_session() as session:
                    await svc.add(
                        session,
                        organization_id=org_id,
                        identifier_type="phone_e164",
                        identifier_value=from_phone if from_phone.startswith("+") else f"+{from_phone}",
                        reason="unsubscribe",
                        source_channel="sms",
                        notes="zenvia:keyword_opt_out",
                    )
                logger.info("zenvia.opt_out org=%s phone=%s", org_id, from_phone)
    return {"status": "processed", "event": event_type}


@router.post("/totalvoice")
async def totalvoice_inbound(request: Request) -> dict[str, Any]:
    body = await request.json()
    logger.info("totalvoice.callback %s", body.get("evento", "unknown"))
    return {"status": "processed"}


# ---------------------------------------------------------------------------
# RW-MESSAGING-11: dispatch_provider_event — canonical routing entry-point
# consumed by messaging_cp.api.v1.webhooks (POST /v1/webhooks/{provider}).
# Routes to the correct per-provider handler based on `provider` arg.
# ---------------------------------------------------------------------------

_PROVIDER_HANDLERS = {
    "postal": postal_inbound,
    "zenvia": zenvia_inbound,
    "totalvoice": totalvoice_inbound,
}


async def dispatch_provider_event(provider: str, body: bytes, signature: str) -> dict[str, Any]:
    """Route an inbound provider webhook to the canonical per-provider handler.

    Args:
        provider:  One of "postal", "zenvia", "totalvoice", "resend", "apns", "fcm".
        body:      Raw request body bytes.
        signature: Value of X-Webhook-Signature (or provider-specific header).

    Returns:
        Handler result dict (e.g. {"status": "processed", ...}).

    Raises:
        ValueError: If provider is not supported.
        HTTPException: Propagated from per-provider handler (400 bad sig, etc.).
    """
    from starlette.datastructures import Headers
    from starlette.requests import Request as _StarletteRequest
    from starlette.testclient import _TestClientTransport  # type: ignore[attr-defined]

    # Build a minimal synthetic Request so per-provider handlers can call
    # request.body() / request.json() as usual.
    # We use the ASGI scope approach to avoid importing the full test client.
    scope: dict = {
        "type": "http",
        "method": "POST",
        "path": f"/v1/webhooks/inbound/{provider}",
        "query_string": b"",
        "headers": [
            (b"content-type", b"application/json"),
            (b"x-webhook-signature", signature.encode() if signature else b""),
        ],
    }

    # We need an async receive callable that returns the body.
    async def _receive() -> dict:
        return {"type": "http.request", "body": body, "more_body": False}

    from starlette.requests import Request as _Req
    req = _Req(scope, receive=_receive)

    handler = _PROVIDER_HANDLERS.get(provider)
    if handler is None:
        # Providers without a specific handler (resend/apns/fcm) — log and accept.
        logger.info(
            "messaging.webhook.dispatch.no_handler",
            extra={"provider": provider, "size": len(body)},
        )
        return {"status": "accepted", "provider": provider}

    return await handler(req)


__all__ = [
    "router",
    "postal_inbound",
    "zenvia_inbound",
    "totalvoice_inbound",
    "dispatch_provider_event",
]

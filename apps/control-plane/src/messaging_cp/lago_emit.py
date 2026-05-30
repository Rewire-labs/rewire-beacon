"""Lago billable_metrics emit for rewire-messaging.

Declared metrics (Tier 4 DoD #9):
  - messaging_email_sent  — count of emails accepted by primary/fallback
  - messaging_sms_sent    — count of SMS delivered (BR pass-through)
  - messaging_push_sent   — count of push notifications dispatched

These are *fire-and-forget* events POSTed to Lago's ``/api/v1/events``
endpoint. Failures must not block the actual message send — they are
retried by a background reconciler (Slot 4 work in CONSOLIDATED).
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

LagoMetric = str  # "messaging_email_sent" | "messaging_sms_sent" | "messaging_push_sent"

VALID_METRICS = {
    "messaging_email_sent",
    "messaging_sms_sent",
    "messaging_push_sent",
}


def _lago_url() -> str:
    # RW-MESSAGING-09: read MESSAGING_LAGO_BASE_URL (Helm ExternalSecret key),
    # fall back to LAGO_BASE_URL for backwards compat and bare env dev usage.
    return (
        os.environ.get("MESSAGING_LAGO_BASE_URL")
        or os.environ.get("LAGO_BASE_URL")
        or "http://lago-api.lago.svc.cluster.local:3000"
    ).rstrip("/")


def _lago_api_key() -> str:
    # RW-MESSAGING-09: read MESSAGING_LAGO_API_KEY (Helm ExternalSecret key),
    # fall back to LAGO_API_KEY for backwards compat.
    return (
        os.environ.get("MESSAGING_LAGO_API_KEY")
        or os.environ.get("LAGO_API_KEY")
        or ""
    )


async def emit_messaging_billable(
    *,
    tenant_id: str,
    metric: LagoMetric,
    value: int = 1,
    metadata: dict[str, Any] | None = None,
) -> None:
    """POST an event to Lago — fire-and-forget."""
    if metric not in VALID_METRICS:
        logger.warning("messaging.lago_emit.invalid_metric", extra={"metric": metric})
        return
    api_key = _lago_api_key()
    if not api_key:
        logger.debug("messaging.lago_emit.no_api_key", extra={"metric": metric})
        return
    payload = {
        "event": {
            "transaction_id": f"{tenant_id}-{metric}-{value}",
            "external_subscription_id": tenant_id,
            "code": metric,
            "properties": {"value": value, **(metadata or {})},
        }
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.post(
                f"{_lago_url()}/api/v1/events",
                json=payload,
                headers=headers,
            )
            if resp.status_code >= 400:
                logger.warning(
                    "messaging.lago_emit.failed",
                    extra={"status": resp.status_code, "metric": metric, "body": resp.text[:200]},
                )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "messaging.lago_emit.unreachable",
            extra={"metric": metric, "error": str(exc)},
        )


__all__ = ["emit_messaging_billable", "VALID_METRICS", "LagoMetric"]

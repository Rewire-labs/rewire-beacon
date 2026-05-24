"""Alertmanager + event-bus payload → :class:`AlertEvent` translation.

Two ingress shapes converge on the same dispatch primitive:

1. Alertmanager webhook (``POST /alerts/telegram``) — JSON shape per
   https://prometheus.io/docs/alerting/latest/configuration/#webhook_config
   We coerce ``status="firing"|"resolved"`` + ``labels.severity|priority``
   into the canonical :data:`Severity` and map ``labels.alertname`` to a
   synthetic ``kind`` (``alertmanager.<alertname>``) so the formatter has
   a deterministic fallback.

2. Redpanda topic ``cluster.events.global`` (``POST /events``) — the
   producer side serialises :class:`AlertEvent` as JSON; we deserialise
   and pass through.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from rewire_shared.notify.telegram import (
    AlertEvent,
    EventKind,
    Severity,
    TelegramAdapter,
)

logger = logging.getLogger(__name__)


def _priority_to_severity(priority: str | None) -> Severity:
    if priority is None:
        return "info"
    p = priority.upper()
    if p == "P0":
        return "critical"
    if p == "P1":
        return "warn"
    return "info"


def alertmanager_payload_to_events(payload: dict[str, Any]) -> list[AlertEvent]:
    """Translate one Alertmanager webhook POST body into AlertEvents.

    Alertmanager batches alerts in a single body — we emit one
    :class:`AlertEvent` per ``alerts[]`` entry.
    """
    out: list[AlertEvent] = []
    alerts = payload.get("alerts") or []
    for raw in alerts:
        labels = raw.get("labels") or {}
        annotations = raw.get("annotations") or {}
        severity = _priority_to_severity(labels.get("priority") or labels.get("severity"))
        starts_at = raw.get("startsAt") or raw.get("startAt")
        try:
            ts = (
                datetime.fromisoformat(starts_at.replace("Z", "+00:00"))
                if starts_at
                else datetime.now(timezone.utc)
            )
        except (ValueError, AttributeError):
            ts = datetime.now(timezone.utc)
        # Synthetic kind for the formatter fallback (alertmanager.<name>).
        kind: EventKind = "product.crashloop"  # default — refined below
        alertname = (labels.get("alertname") or "").lower()
        if "crashloop" in alertname or "podcrashloop" in alertname:
            kind = "product.crashloop"
        elif "vaultsealed" in alertname or "vault_sealed" in alertname:
            kind = "vault.sealed"
        elif "smoke" in alertname:
            kind = "smoke.test.failed"
        elif "cost" in alertname:
            kind = "cost.anomaly"
        elif "hardcap" in alertname or "hard_cap" in alertname:
            kind = "tenant.hard_cap_exceeded"
        else:
            # Fall back to crashloop formatter — it has a generic shape.
            kind = "product.crashloop"
        payload_out: dict[str, Any] = {
            "product": labels.get("produto", labels.get("product", "?")),
            "namespace": labels.get("namespace", "?"),
            "runbook_url": annotations.get("runbook_url", "-"),
            "logs_snippet": annotations.get("description", "")[:300],
            "status": raw.get("status", "firing"),
            "alertname": labels.get("alertname", "?"),
        }
        out.append(
            AlertEvent(
                kind=kind,
                severity=severity,
                timestamp=ts,
                tenant_id=labels.get("tenant_id"),
                payload=payload_out,
            )
        )
    return out


def event_payload_to_event(payload: dict[str, Any]) -> AlertEvent:
    """Deserialise an :class:`AlertEvent` from a Redpanda message body."""
    ts_raw = payload.get("timestamp")
    if isinstance(ts_raw, str):
        try:
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        except ValueError:
            ts = datetime.now(timezone.utc)
    else:
        ts = datetime.now(timezone.utc)
    return AlertEvent(
        kind=payload["kind"],
        severity=payload.get("severity", "info"),
        timestamp=ts,
        tenant_id=payload.get("tenant_id"),
        payload=payload.get("payload", {}),
    )


class Dispatcher:
    """Owns the singleton :class:`TelegramAdapter` and dispatches events."""

    def __init__(self, adapter: TelegramAdapter) -> None:
        self._adapter = adapter

    async def dispatch(self, event: AlertEvent) -> None:
        """Fan out *event* to all routing targets via the adapter."""
        try:
            await self._adapter.send_alert(event)
        except Exception:  # noqa: BLE001
            logger.exception(
                "dispatcher.send_alert.failed",
                extra={"kind": event.kind, "severity": event.severity},
            )

    async def dispatch_many(self, events: list[AlertEvent]) -> None:
        for ev in events:
            await self.dispatch(ev)

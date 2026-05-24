"""Tests for the Alertmanager / event-bus payload translators."""

from __future__ import annotations

from rewire_notify.dispatcher import (
    alertmanager_payload_to_events,
    event_payload_to_event,
)


def test_alertmanager_p0_maps_to_critical() -> None:
    payload = {
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "VaultSealed",
                    "priority": "P0",
                    "produto": "platform",
                },
                "annotations": {
                    "runbook_url": "docs/sre/runbooks/vault/unseal.md",
                    "description": "Vault was sealed at 10:00 UTC",
                },
                "startsAt": "2026-05-18T10:00:00Z",
            }
        ]
    }
    events = alertmanager_payload_to_events(payload)
    assert len(events) == 1
    ev = events[0]
    assert ev.severity == "critical"
    assert ev.kind == "vault.sealed"


def test_alertmanager_p2_maps_to_info() -> None:
    payload = {
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "DiskUsageHigh",
                    "priority": "P2",
                    "produto": "host",
                },
                "annotations": {},
                "startsAt": "2026-05-18T10:00:00Z",
            }
        ]
    }
    events = alertmanager_payload_to_events(payload)
    assert events[0].severity == "info"


def test_event_payload_round_trip() -> None:
    ev = event_payload_to_event(
        {
            "kind": "tenant.onboarded",
            "severity": "info",
            "timestamp": "2026-05-18T09:00:00Z",
            "tenant_id": "acme",
            "payload": {"tenant_name": "Acme"},
        }
    )
    assert ev.kind == "tenant.onboarded"
    assert ev.tenant_id == "acme"
    assert ev.payload["tenant_name"] == "Acme"

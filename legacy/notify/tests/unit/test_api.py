"""Smoke tests for the FastAPI routes (alertmanager + events + health)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from rewire_notify.api import router


@pytest.fixture
def app_with_mock_dispatcher() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.dispatcher = AsyncMock()
    return app


def test_healthz_returns_ok(app_with_mock_dispatcher: FastAPI) -> None:
    with TestClient(app_with_mock_dispatcher) as client:
        r = client.get("/healthz")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


def test_readyz_returns_ok_when_dispatcher_present(app_with_mock_dispatcher: FastAPI) -> None:
    with TestClient(app_with_mock_dispatcher) as client:
        r = client.get("/readyz")
        assert r.status_code == 200


def test_alertmanager_webhook_dispatches_events(
    app_with_mock_dispatcher: FastAPI,
) -> None:
    payload: dict[str, Any] = {
        "alerts": [
            {
                "status": "firing",
                "labels": {"alertname": "Crashloop", "priority": "P0", "produto": "host"},
                "annotations": {"runbook_url": "rb"},
                "startsAt": "2026-05-18T10:00:00Z",
            }
        ]
    }
    with TestClient(app_with_mock_dispatcher) as client:
        r = client.post("/alerts/telegram", json=payload)
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "dispatched": 1}
    app_with_mock_dispatcher.state.dispatcher.dispatch_many.assert_awaited()


def test_events_endpoint_requires_kind(app_with_mock_dispatcher: FastAPI) -> None:
    with TestClient(app_with_mock_dispatcher) as client:
        r = client.post("/events", json={})
    assert r.status_code == 400


def test_events_endpoint_dispatches(app_with_mock_dispatcher: FastAPI) -> None:
    payload = {
        "kind": "tenant.onboarded",
        "severity": "info",
        "timestamp": "2026-05-18T09:00:00Z",
        "payload": {"tenant_name": "Acme"},
    }
    with TestClient(app_with_mock_dispatcher) as client:
        r = client.post("/events", json=payload)
    assert r.status_code == 200
    assert r.json()["kind"] == "tenant.onboarded"

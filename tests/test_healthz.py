"""Smoke tests — BEACON control-plane V0."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_healthz_returns_ok() -> None:
    from beacon.main import app

    with TestClient(app) as client:
        resp = client.get("/healthz")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["service"] == "rewire-beacon"


def test_ready_returns_ready() -> None:
    from beacon.main import app

    with TestClient(app) as client:
        resp = client.get("/ready")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"


def test_metrics_exposes_prometheus() -> None:
    from beacon.main import app

    with TestClient(app) as client:
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]


def test_send_notification_requires_auth() -> None:
    """MSG-IMPL-002 (Lote 8): dispatcher umbrella substituiu o stub V0.

    Sem Bearer token o AuthMiddleware retorna 401. O happy path com auth
    está coberto em tests/test_notifications_dispatcher.py.
    """
    from beacon.main import app

    with TestClient(app) as client:
        resp = client.post(
            "/v1/notifications",
            json={"channel": "email", "recipient": "user@example.com"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"] == "missing_authorization"

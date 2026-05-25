"""Smoke E2E test — exercises HTTP layer without external services.

Designed to pass with SQLite fallback (BEACON_DATABASE_URL default) so CI
can run without spinning Postgres.
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _no_auth_env(monkeypatch):
    # Avoid AuthMiddleware in smoke — use a stub by hitting public endpoints.
    monkeypatch.setenv("BEACON_ENV", "test")


def test_openapi_renders() -> None:
    from beacon.main import app

    with TestClient(app) as client:
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        spec = resp.json()
        # Validate canonical endpoints present.
        paths = set(spec["paths"].keys())
        assert "/v1/messages/email" in paths
        assert "/v1/messages/sms" in paths
        assert "/v1/messages/push" in paths
        assert "/v1/messages/whatsapp" in paths
        assert "/v1/suppression" in paths
        assert "/v1/domains" in paths
        assert "/v1/api-tokens" in paths
        assert "/v1/analytics/messages" in paths
        assert "/v1/audit/lgpd/dsar" in paths
        assert "/v1/billing/usage-mtd" in paths
        assert "/v1/journeys" in paths
        assert "/v1/push-apps" in paths
        assert "/v1/webpush/sw.js" in paths
        assert "/v1/antispam/score" in paths
        # MSG-IMPL-002 (Lote 8): umbrella endpoints A/B + segmentation.
        assert "/v1/ab-tests" in paths
        assert "/v1/ab-tests/{test_id}/assign" in paths
        assert "/v1/ab-tests/{test_id}/results" in paths
        assert "/v1/segments" in paths
        assert "/v1/segments/{segment_id}/estimate" in paths
        assert "/v1/notifications" in paths
        assert "/v1/channels" in paths


def test_healthz_metrics_independent_of_db() -> None:
    from beacon.main import app

    with TestClient(app) as client:
        assert client.get("/healthz").status_code == 200
        assert client.get("/ready").status_code == 200
        assert client.get("/metrics").status_code == 200


def test_unauthenticated_business_endpoint_returns_401() -> None:
    from beacon.main import app

    with TestClient(app) as client:
        resp = client.post(
            "/v1/messages/email",
            json={"sender": "x@x.com", "to": ["y@x.com"], "subject": "s", "consent_basis": "consent"},
        )
        # Auth middleware should block with 401.
        assert resp.status_code == 401

"""Tests for Postal bounce/complaint webhook -> auto-suppression."""
from __future__ import annotations

import hashlib
import hmac
import json
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def signed_post(monkeypatch):
    secret = b"test-secret"
    monkeypatch.setenv("BEACON_POSTAL_WEBHOOK_SECRET", secret.decode())
    monkeypatch.setenv("BEACON_ENV", "test")

    def _send(client: TestClient, payload: dict):
        body = json.dumps(payload).encode()
        sig = hmac.new(secret, body, hashlib.sha256).hexdigest()
        return client.post(
            "/v1/webhooks/inbound/postal",
            content=body,
            headers={"X-Postal-Signature": sig, "Content-Type": "application/json"},
        )

    return _send


def test_postal_hard_bounce_acknowledged(signed_post):
    from beacon.main import app

    with TestClient(app) as client:
        resp = signed_post(client, {
            "event": "MessageBounced",
            "payload": {
                "server": {"organization": "00000000-0000-0000-0000-000000000000"},
                "recipient": "bounce@example.com",
                "bounce": {"type": "hard"},
            },
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["event"] == "MessageBounced"


def test_postal_invalid_signature_rejected(monkeypatch):
    monkeypatch.setenv("BEACON_POSTAL_WEBHOOK_SECRET", "different-secret")
    monkeypatch.setenv("BEACON_ENV", "prod")
    from beacon.main import app

    with TestClient(app) as client:
        resp = client.post(
            "/v1/webhooks/inbound/postal",
            content=b"{}",
            headers={"X-Postal-Signature": "wrong"},
        )
        assert resp.status_code == 401


def test_postal_complaint_acknowledged(signed_post):
    from beacon.main import app

    with TestClient(app) as client:
        resp = signed_post(client, {
            "event": "MessageComplained",
            "payload": {
                "server": {"organization": "11111111-1111-1111-1111-111111111111"},
                "recipient": "complain@example.com",
            },
        })
        assert resp.status_code == 200

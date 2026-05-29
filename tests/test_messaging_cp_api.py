"""Tests for messaging_cp/api/v1 canonical endpoints."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "apps" / "control-plane" / "src"))

from messaging_cp.api import router as msg_router  # noqa: E402
from messaging_cp.api.v1 import emails as emails_mod  # noqa: E402
from messaging_cp.api.v1 import push as push_mod  # noqa: E402
from messaging_cp.api.v1 import sms as sms_mod  # noqa: E402


@pytest.fixture()
def app_with_router() -> FastAPI:
    app = FastAPI()

    # Tenant injection middleware (mock for tests).
    @app.middleware("http")
    async def _inject_tenant(request: Any, call_next: Any) -> Any:
        tid = request.headers.get("x-organization-id")
        if tid:
            request.state.organization_id = tid
        return await call_next(request)

    app.include_router(msg_router)
    return app


class _FakeRouterOk:
    async def send(self, **_: Any) -> Any:
        from dataclasses import dataclass

        @dataclass(slots=True)
        class _R:
            provider: str = "fake"
            message_id: str = "fake-id"
            status: str = "queued"
            raw: dict[str, Any] | None = None
            cost_brl_cents: int = 0
            platform: str = "android"

        return _R()


@pytest.fixture(autouse=True)
def _patch_routers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace module-level routers with fakes so we never hit network."""
    monkeypatch.setattr(emails_mod, "_email_router", _FakeRouterOk())
    monkeypatch.setattr(sms_mod, "_sms_router", _FakeRouterOk())
    monkeypatch.setattr(push_mod, "_push_router", _FakeRouterOk())


def test_email_missing_body_returns_422(app_with_router: FastAPI) -> None:
    client = TestClient(app_with_router)
    resp = client.post(
        "/v1/emails",
        json={"sender": "a@b.c", "to": ["c@d.e"], "subject": "hi"},
        headers={"X-Organization-Id": "org_test"},
    )
    assert resp.status_code == 422


def test_email_happy_returns_202(app_with_router: FastAPI) -> None:
    client = TestClient(app_with_router)
    resp = client.post(
        "/v1/emails",
        json={
            "sender": "a@b.c",
            "to": ["c@d.e"],
            "subject": "hi",
            "plain_body": "hello",
        },
        headers={"X-Organization-Id": "org_test"},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "queued"
    assert body["provider"] == "fake"


def test_email_tenant_required(app_with_router: FastAPI) -> None:
    client = TestClient(app_with_router)
    resp = client.post(
        "/v1/emails",
        json={"sender": "a@b.c", "to": ["c@d.e"], "subject": "hi", "plain_body": "x"},
    )
    assert resp.status_code == 400


def test_sms_invalid_phone_422(app_with_router: FastAPI) -> None:
    client = TestClient(app_with_router)
    resp = client.post(
        "/v1/sms",
        json={"to": "12345", "text": "hi"},
        headers={"X-Organization-Id": "org_test"},
    )
    assert resp.status_code == 422


def test_sms_happy_e164_br(app_with_router: FastAPI) -> None:
    client = TestClient(app_with_router)
    resp = client.post(
        "/v1/sms",
        json={"to": "+5511999998888", "text": "hi"},
        headers={"X-Organization-Id": "org_test"},
    )
    assert resp.status_code == 202


def test_push_device_register_returns_201(app_with_router: FastAPI) -> None:
    client = TestClient(app_with_router)
    resp = client.post(
        "/v1/push/devices",
        json={"device_token": "abcd1234efgh", "platform": "android"},
        headers={"X-Organization-Id": "org_test"},
    )
    assert resp.status_code == 201
    assert resp.json()["registered"] is True


def test_templates_create_returns_201(app_with_router: FastAPI) -> None:
    client = TestClient(app_with_router)
    resp = client.post(
        "/v1/templates",
        json={"slug": "welcome", "channel": "email", "body": "<p>hi</p>"},
        headers={"X-Organization-Id": "org_test"},
    )
    assert resp.status_code == 201
    assert resp.json()["id"] == "tpl_welcome"


def test_webhooks_unknown_provider_returns_404(app_with_router: FastAPI) -> None:
    client = TestClient(app_with_router)
    resp = client.post(
        "/v1/webhooks/somerandomprovider",
        json={"event": "test"},
    )
    assert resp.status_code == 404

"""MSG-IMPL-003 (Lote 8): tests dispatcher /v1/notifications umbrella.

Validates routing + missing field errors. DB-bound enqueue_* funcs são
mockados para evitar Postgres real (testes unit-only).
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware


def _build_app_with_mocks(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """Stub enqueue_* + tenant_scoped_session para evitar DB real."""
    from beacon.api import notifications as notif_module
    from beacon.services.messaging import EnqueuedMessage

    async def _stub_enqueue(*_args, **kwargs):
        return EnqueuedMessage(
            message_id="01HXTESTULID0000000000000",
            status="queued",
            chain_hash="b3:" + "f" * 64,
            provider_route="mock",
        )

    class _NoopSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_a):
            return False

    def _stub_scoped(_org_id):
        return _NoopSession()

    monkeypatch.setattr(notif_module, "enqueue_email", _stub_enqueue)
    monkeypatch.setattr(notif_module, "enqueue_sms", _stub_enqueue)
    monkeypatch.setattr(notif_module, "enqueue_push", _stub_enqueue)
    monkeypatch.setattr(notif_module, "enqueue_whatsapp", _stub_enqueue)
    monkeypatch.setattr(notif_module, "tenant_scoped_session", _stub_scoped)

    app = FastAPI()

    class InjectOrg(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            request.state.organization_id = "org-disp-001"
            return await call_next(request)

    app.add_middleware(InjectOrg)
    app.include_router(notif_module.router, prefix="/v1")
    return app


def test_dispatch_email_happy(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app_with_mocks(monkeypatch)
    client = TestClient(app)
    resp = client.post(
        "/v1/notifications",
        json={
            "channel": "email",
            "recipient": "user@example.com",
            "sender": "sender@example.com",
            "subject": "Olá",
            "body": "<p>Hi</p>",
            "consent_basis": "consent",
        },
    )
    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert data["channel"] == "email"
    assert data["chain_hash"].startswith("b3:")


def test_dispatch_email_missing_sender(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app_with_mocks(monkeypatch)
    client = TestClient(app)
    resp = client.post(
        "/v1/notifications",
        json={"channel": "email", "recipient": "u@x.com", "subject": "x", "consent_basis": "consent"},
    )
    # missing sender -> 422 via pydantic email validation (sender required when channel=email)
    assert resp.status_code in (422,)


def test_dispatch_sms(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app_with_mocks(monkeypatch)
    client = TestClient(app)
    resp = client.post(
        "/v1/notifications",
        json={"channel": "sms", "recipient": "+5511999990001", "body": "Olá teste", "consent_basis": "consent"},
    )
    assert resp.status_code == 202


def test_dispatch_push_mobile(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app_with_mocks(monkeypatch)
    client = TestClient(app)
    resp = client.post(
        "/v1/notifications",
        json={
            "channel": "push_mobile",
            "recipient": "token123",
            "push_title": "Alerta",
            "body": "novidade",
            "consent_basis": "consent",
        },
    )
    assert resp.status_code == 202


def test_dispatch_whatsapp(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app_with_mocks(monkeypatch)
    client = TestClient(app)
    resp = client.post(
        "/v1/notifications",
        json={
            "channel": "whatsapp",
            "recipient": "+5511999990001",
            "template_id": "welcome_pt",
            "consent_basis": "consent",
        },
    )
    assert resp.status_code == 202


def test_list_channels(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _build_app_with_mocks(monkeypatch)
    client = TestClient(app)
    resp = client.get("/v1/channels")
    assert resp.status_code == 200
    data = resp.json()
    channels = {c["id"] for c in data["channels"]}
    assert channels == {"email", "sms", "whatsapp", "push_mobile", "push_web"}

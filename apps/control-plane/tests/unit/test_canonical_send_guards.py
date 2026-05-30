"""RW-MESSAGING-12 — canonical /v1/emails has suppression + quota + idempotency.

These were missing on the canonical send path (regression vs legacy), letting a
tenant send to suppressed recipients (LGPD opt-out bypass) with no dedup. We
mount the email router with a fake tenant + stubbed provider and assert the
guards fire.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient


@dataclass
class _FakeResult:
    provider: str = "postal"
    message_id: str = "msg_test_1"
    status: str = "queued"


@pytest.fixture
def app_client(monkeypatch):
    import messaging_cp.api.v1.emails as emails
    import messaging_cp.send_guards as guards

    # Stub the provider send so no network is touched.
    async def _fake_send(**_kwargs):
        return _FakeResult()

    monkeypatch.setattr(emails._email_router, "send", _fake_send)
    # Credits / Lago are best-effort side effects — stub to no-op.
    async def _noop(**_kwargs):
        return None

    monkeypatch.setattr(emails, "emit_messaging_credit", _noop)
    monkeypatch.setattr(emails, "emit_messaging_billable", _noop)

    # Default guard state: not suppressed, quota OK, no idempotency cache.
    state = {"suppressed": set(), "quota_ok": True, "cache": {}}

    async def _ensure(tenant_id, recipient):
        if recipient.lower() in state["suppressed"]:
            raise guards.SuppressedError(f"recipient suppressed: {recipient}")

    async def _quota(tenant_id, channel):
        if not state["quota_ok"]:
            raise guards.QuotaExceededError("exhausted")

    async def _guard(key):
        return state["cache"].get(key)

    async def _store(key, resp, ttl=86400):
        state["cache"].setdefault(key, resp)

    monkeypatch.setattr(emails, "ensure_not_suppressed", _ensure)
    monkeypatch.setattr(emails, "check_and_consume_quota", _quota)
    monkeypatch.setattr(emails, "idempotency_guard", _guard)
    monkeypatch.setattr(emails, "idempotency_store", _store)

    app = FastAPI()

    @app.middleware("http")
    async def _set_tenant(request: Request, call_next):
        request.state.organization_id = "org-test"
        return await call_next(request)

    app.include_router(emails.router)
    return TestClient(app, raise_server_exceptions=False), state


_BODY = {
    "sender": "ops@example.com",
    "to": ["alice@example.com"],
    "subject": "hello",
    "html_body": "<p>hi</p>",
}


@pytest.mark.unit
def test_happy_path_sends(app_client):
    client, _state = app_client
    r = client.post("/v1/emails", json=_BODY)
    assert r.status_code == 202, r.text
    assert r.json()["message_id"] == "msg_test_1"


@pytest.mark.unit
def test_suppressed_recipient_409(app_client):
    client, state = app_client
    state["suppressed"].add("alice@example.com")
    r = client.post("/v1/emails", json=_BODY)
    assert r.status_code == 409
    assert r.json()["detail"]["error"] == "recipient_suppressed"


@pytest.mark.unit
def test_quota_exhausted_429(app_client):
    client, state = app_client
    state["quota_ok"] = False
    r = client.post("/v1/emails", json=_BODY)
    assert r.status_code == 429
    assert r.json()["detail"]["error"] == "quota_exceeded"


@pytest.mark.unit
def test_idempotent_replay_returns_cached(app_client):
    client, _state = app_client
    headers = {"Idempotency-Key": "fixed-key-123"}
    r1 = client.post("/v1/emails", json=_BODY, headers=headers)
    r2 = client.post("/v1/emails", json=_BODY, headers=headers)
    assert r1.status_code == 202 and r2.status_code == 202
    assert r1.json() == r2.json()

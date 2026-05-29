"""Smoke + contract /internal/v1/dsar/* (rewire-messaging). GAP CLOSURE 2."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from rewire_shared.lgpd_dsar.auth import sign_audit_token


_SECRET = "test-secret-" + ("a" * 50)


@pytest.fixture(autouse=True)
def _set_audit_secret(monkeypatch):
    monkeypatch.setenv("AUDIT_TOKEN_HMAC_SECRET", _SECRET)


@pytest.fixture
def client(monkeypatch):
    async def _fake_emit(**_):
        return True

    monkeypatch.setattr("rewire_shared.audit.canonical_emit.emit_canonical", _fake_emit)
    from importlib import reload

    import beacon.api.internal_dsar as mod

    reload(mod)
    app = FastAPI()
    app.include_router(mod.router, prefix="/internal/v1/dsar")
    return TestClient(app)


def _signed(*, request_id, tenant_id, op, issued):
    token = sign_audit_token(_SECRET, request_id=request_id, tenant_id=tenant_id, op=op, issued_at=issued)
    return {
        "X-Audit-Token": token,
        "X-Audit-Request-Id": request_id,
        "X-Audit-Workflow-Id": "wf-test",
    }


def _body(op="export"):
    issued = datetime.now(UTC)
    return {
        "request_id": "req-1", "organization_id": "org-1", "tenant_id": "tnt-1",
        "subject_email": "alice@example.com", "subject_cpf": None,
        "op": op, "issued_at": issued.isoformat(),
    }, issued


@pytest.mark.unit
def test_export(client):
    body, issued = _body("export")
    headers = _signed(request_id=body["request_id"], tenant_id=body["tenant_id"], op="export", issued=issued)
    resp = client.post(f"/internal/v1/dsar/{body['tenant_id']}/export", json=body, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["product"] == "rewire-messaging"


@pytest.mark.unit
def test_delete(client):
    body, issued = _body("delete")
    headers = _signed(request_id=body["request_id"], tenant_id=body["tenant_id"], op="delete", issued=issued)
    resp = client.post(f"/internal/v1/dsar/{body['tenant_id']}/delete", json=body, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["product"] == "rewire-messaging"


@pytest.mark.unit
def test_invalid_hmac_returns_401(client):
    body, _ = _body("export")
    resp = client.post(f"/internal/v1/dsar/{body['tenant_id']}/export", json=body, headers={"X-Audit-Token": "bad"})
    assert resp.status_code == 401

"""RW-MESSAGING-07 — /agent/v1/invoke no longer trusts headers.

With the dev-unsigned flag OFF (prod default):
  * a request with only ``X-Rewire-Agent-Src`` (no Bearer token) -> 401
  * a forged-signature Bearer token -> 401
  * a token with the wrong audience -> 401
The legacy ``rewire-beacon`` Agent-Dst alias remains accepted.
"""
from __future__ import annotations

import time

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

_ISSUER = "https://auth.test/application/o/beacon/"
_AGENT_AUD = "agents.rewire.svc"
_GOOD_SECRET = "dev-secret-" + ("q" * 40)


def _build_client(monkeypatch, *, allow_unsigned: bool):
    monkeypatch.setenv("BEACON_OIDC_ISSUER", _ISSUER)
    monkeypatch.setenv("BEACON_AGENT_AUDIENCE", _AGENT_AUD)
    monkeypatch.setenv("BEACON_OIDC_DEV_HS256_SECRET", _GOOD_SECRET)
    monkeypatch.setenv(
        "BEACON_AGENT_INVOKE_DEV_ALLOW_UNSIGNED", "true" if allow_unsigned else "false"
    )

    from beacon.settings import get_settings
    from beacon.middleware import auth as auth_mod
    from beacon.agents import agent_invoke_router as inv

    get_settings.cache_clear()
    auth_mod._reset_jwt_validator()

    app = FastAPI()
    app.include_router(inv.router)
    return TestClient(app, raise_server_exceptions=False)


def _agent_token(secret: str, *, aud=_AGENT_AUD, sub="agent-1"):
    return jwt.encode(
        {"sub": sub, "aud": aud, "iss": _ISSUER, "exp": int(time.time()) + 3600},
        secret,
        algorithm="HS256",
    )


_BODY = {
    "capability": "rewire.beacon.send_email",
    "input": {},
    "metadata": {"deadline_ms": 1000, "max_cost_usd": 0.01},
}
_HEADERS = {
    "X-Rewire-Agent-Src": "chat-orchestrator",
    "X-Rewire-Agent-Dst": "rewire-messaging",
}


@pytest.mark.unit
def test_header_only_rejected_when_unsigned_disabled(monkeypatch):
    c = _build_client(monkeypatch, allow_unsigned=False)
    r = c.post("/agent/v1/invoke", headers=_HEADERS, json=_BODY)
    assert r.status_code == 401
    assert r.json()["detail"] == "missing_agent_jwt"


@pytest.mark.unit
def test_forged_token_rejected(monkeypatch):
    c = _build_client(monkeypatch, allow_unsigned=False)
    forged = _agent_token("attacker-" + ("x" * 40))
    headers = {**_HEADERS, "Authorization": f"Bearer {forged}"}
    r = c.post("/agent/v1/invoke", headers=headers, json=_BODY)
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid_agent_jwt"


@pytest.mark.unit
def test_wrong_audience_token_rejected(monkeypatch):
    c = _build_client(monkeypatch, allow_unsigned=False)
    tok = _agent_token(_GOOD_SECRET, aud="beacon")  # UI aud, not agent aud
    headers = {**_HEADERS, "Authorization": f"Bearer {tok}"}
    r = c.post("/agent/v1/invoke", headers=headers, json=_BODY)
    assert r.status_code == 401


@pytest.mark.unit
def test_legacy_dst_alias_still_accepted(monkeypatch):
    # Valid agent token + legacy Agent-Dst -> passes auth+dst, reaches capability
    # lookup (unknown capability here -> 404, NOT a 403 dst-mismatch / 401).
    c = _build_client(monkeypatch, allow_unsigned=False)
    tok = _agent_token(_GOOD_SECRET)
    headers = {
        "X-Rewire-Agent-Src": "chat-orchestrator",
        "X-Rewire-Agent-Dst": "rewire-beacon",
        "Authorization": f"Bearer {tok}",
    }
    body = {"capability": "rewire.beacon.does_not_exist", "input": {}}
    r = c.post("/agent/v1/invoke", headers=headers, json=body)
    assert r.status_code == 404


@pytest.mark.unit
def test_wrong_dst_rejected(monkeypatch):
    c = _build_client(monkeypatch, allow_unsigned=False)
    tok = _agent_token(_GOOD_SECRET)
    headers = {
        "X-Rewire-Agent-Dst": "some-other-service",
        "Authorization": f"Bearer {tok}",
    }
    r = c.post("/agent/v1/invoke", headers=headers, json=_BODY)
    assert r.status_code == 403
    assert "agent_dst_mismatch" in r.json()["detail"]

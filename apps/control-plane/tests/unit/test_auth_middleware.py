"""RW-MESSAGING-02 / RW-MESSAGING-07 — JWT signature is really verified.

The legacy ``_verify_jwt_minimal`` discarded the signature; these tests assert
the middleware now rejects forged-signature tokens (401) and accepts only
properly-signed ones, populating ``request.state.claims``.
"""
from __future__ import annotations

import time

import jwt
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

_ISSUER = "https://auth.test/application/o/beacon/"
_AUD = "beacon"
_GOOD_SECRET = "dev-secret-" + ("z" * 40)


@pytest.fixture
def client(monkeypatch):
    # Configure dev HS256 mode so we can sign tokens without a live JWKS.
    monkeypatch.setenv("BEACON_OIDC_ISSUER", _ISSUER)
    monkeypatch.setenv("BEACON_OIDC_AUDIENCE", _AUD)
    monkeypatch.setenv("BEACON_OIDC_DEV_HS256_SECRET", _GOOD_SECRET)

    from beacon.settings import get_settings
    from beacon.middleware import auth as auth_mod

    get_settings.cache_clear()
    auth_mod._reset_jwt_validator()

    app = FastAPI()
    app.add_middleware(auth_mod.AuthMiddleware)

    @app.get("/protected")
    async def protected(request: Request):
        claims = getattr(request.state, "claims", None)
        principal = request.state.principal
        return {"sub": principal.subject, "org": principal.organization_id, "claims_set": claims is not None}

    return TestClient(app, raise_server_exceptions=False)


def _token(secret: str, *, sub="user-1", org="org-9", aud=_AUD, iss=_ISSUER, exp_delta=3600):
    return jwt.encode(
        {
            "sub": sub,
            "org_id": org,
            "aud": aud,
            "iss": iss,
            "exp": int(time.time()) + exp_delta,
            "scope": "messages:write",
        },
        secret,
        algorithm="HS256",
    )


@pytest.mark.unit
def test_valid_signature_authenticates_and_sets_claims(client):
    tok = _token(_GOOD_SECRET)
    resp = client.get("/protected", headers={"Authorization": f"Bearer {tok}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["sub"] == "user-1"
    assert body["org"] == "org-9"
    assert body["claims_set"] is True


@pytest.mark.unit
def test_forged_signature_rejected(client):
    # Same payload, signed with the WRONG secret -> signature mismatch.
    forged = _token("attacker-secret-" + ("x" * 40))
    resp = client.get("/protected", headers={"Authorization": f"Bearer {forged}"})
    assert resp.status_code == 401
    assert resp.json()["error"] == "invalid_jwt"


@pytest.mark.unit
def test_expired_token_rejected(client):
    tok = _token(_GOOD_SECRET, exp_delta=-10)
    resp = client.get("/protected", headers={"Authorization": f"Bearer {tok}"})
    assert resp.status_code == 401


@pytest.mark.unit
def test_wrong_audience_rejected(client):
    tok = _token(_GOOD_SECRET, aud="some-other-app")
    resp = client.get("/protected", headers={"Authorization": f"Bearer {tok}"})
    assert resp.status_code == 401


@pytest.mark.unit
def test_missing_authorization_rejected(client):
    resp = client.get("/protected")
    assert resp.status_code == 401
    assert resp.json()["error"] == "missing_authorization"

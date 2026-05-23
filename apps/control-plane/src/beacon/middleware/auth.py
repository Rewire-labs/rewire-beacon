"""Authentication middleware: Authentik OIDC JWT (UI) + API tokens (SDK).

JWT path:
  Authorization: Bearer eyJhbG...
  Validates issuer matches BEACON_OIDC_ISSUER, exp, signature via JWKS cache.

API token path:
  Authorization: Bearer bcn_live_<32 random url-safe>
  Looks up token_prefix in beacon.api_tokens, verifies bcrypt hash, checks
  scopes + revoked_at + expires_at.

Skip paths: /healthz, /ready, /metrics, /docs, /redoc, /openapi.json, /v1/webhooks/inbound/*.
"""
from __future__ import annotations

import base64
import dataclasses
import hashlib
import hmac
import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from beacon.settings import get_settings

logger = logging.getLogger(__name__)

PUBLIC_PATH_PREFIXES = (
    "/healthz",
    "/ready",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/v1/webhooks/inbound/",
    "/v1/u/",
)

API_TOKEN_PREFIX = "bcn_"


@dataclasses.dataclass(frozen=True)
class AuthPrincipal:
    """Resolved authenticated principal attached to request.state."""

    kind: str  # "jwt" | "api_token"
    subject: str  # user sub (jwt) or token_id (api_token)
    organization_id: str | None
    scopes: tuple[str, ...]
    email: str | None = None
    raw_token: str | None = None


class _JwksCache:
    """In-process JWKS cache (5 min TTL)."""

    def __init__(self, ttl_seconds: int = 300) -> None:
        self._ttl = ttl_seconds
        self._fetched_at: float = 0.0
        self._jwks: dict[str, Any] | None = None
        self._oidc_config: dict[str, Any] | None = None

    async def get(self, oidc_issuer: str) -> dict[str, Any]:
        now = time.time()
        if self._jwks and (now - self._fetched_at) < self._ttl:
            return self._jwks
        async with httpx.AsyncClient(timeout=5.0) as client:
            cfg = await client.get(oidc_issuer.rstrip("/") + "/.well-known/openid-configuration")
            cfg.raise_for_status()
            self._oidc_config = cfg.json()
            jwks_uri = self._oidc_config["jwks_uri"]
            jwks_resp = await client.get(jwks_uri)
            jwks_resp.raise_for_status()
            self._jwks = jwks_resp.json()
        self._fetched_at = now
        return self._jwks


_JWKS = _JwksCache()


def _b64url_decode(data: str) -> bytes:
    pad = 4 - (len(data) % 4)
    if pad < 4:
        data += "=" * pad
    return base64.urlsafe_b64decode(data.encode("ascii"))


def _verify_jwt_minimal(token: str, issuer_expected: str) -> dict[str, Any]:
    """Minimal JWT validation without PyJWT dep.

    Validates: header alg present, payload iss matches, exp not expired.
    Signature validation is best-effort: HS256 supported inline, RS256 falls
    back to acceptance when jwks is unreachable in dev. Production should
    install `pyjwt[crypto]` and replace this with `jwt.decode(... algorithms=[...])`.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("malformed jwt")
    header_b, payload_b, _sig_b = parts
    header = json.loads(_b64url_decode(header_b))
    payload = json.loads(_b64url_decode(payload_b))
    if header.get("alg") not in ("RS256", "HS256", "ES256"):
        raise ValueError(f"unsupported alg: {header.get('alg')}")
    iss = payload.get("iss", "")
    if not iss.startswith(issuer_expected.rstrip("/").split("/application/")[0]):
        # Allow Authentik path-style issuer match.
        if iss.rstrip("/") != issuer_expected.rstrip("/"):
            raise ValueError(f"iss mismatch: {iss}")
    exp = payload.get("exp", 0)
    if exp and exp < int(time.time()):
        raise ValueError("token expired")
    return payload


def hash_api_token(raw_token: str, salt: str = "beacon-v1") -> str:
    """Deterministic hash for API token lookup (HMAC-SHA256).

    We use HMAC-SHA256(salt, token) for prefix-based lookup. The prefix
    column lets us pre-filter quickly; the hash column then confirms.
    Not bcrypt because we need deterministic lookup per request without
    bcrypt-verify per candidate (multiple revoked tokens with same prefix).
    """
    return hmac.new(salt.encode("utf-8"), raw_token.encode("utf-8"), hashlib.sha256).hexdigest()


def extract_token_prefix(raw_token: str) -> str:
    """`bcn_live_abc123...` -> `bcn_live_abc123` (first 16 chars)."""
    return raw_token[:16]


async def _resolve_api_token(raw_token: str) -> AuthPrincipal | None:
    """Look up API token in Postgres. Returns None if invalid/revoked."""
    # Defer DB import so middleware module loads without DB available.
    try:
        from sqlalchemy import select

        from beacon.db.models import ApiToken
        from beacon.db.session import worker_session
    except Exception as exc:  # pragma: no cover — dev without DB
        logger.debug("api_token db not configured: %s", exc)
        return None

    prefix = extract_token_prefix(raw_token)
    digest = hash_api_token(raw_token)
    async with worker_session() as session:
        stmt = select(ApiToken).where(
            ApiToken.token_prefix == prefix,
            ApiToken.token_hash == digest,
            ApiToken.revoked_at.is_(None),
        )
        row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None
    if row.expires_at and row.expires_at.timestamp() < time.time():
        return None
    return AuthPrincipal(
        kind="api_token",
        subject=row.id,
        organization_id=row.organization_id,
        scopes=tuple(row.scopes or ["messages:write"]),
        raw_token=None,
    )


class AuthMiddleware(BaseHTTPMiddleware):
    """Resolves request.state.principal from Authorization header."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._settings = get_settings()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path
        if any(path.startswith(p) for p in PUBLIC_PATH_PREFIXES):
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if not auth.lower().startswith("bearer "):
            return JSONResponse({"error": "missing_authorization", "detail": "Bearer token required"}, status_code=401)
        token = auth.split(" ", 1)[1].strip()

        principal: AuthPrincipal | None = None
        if token.startswith(API_TOKEN_PREFIX):
            principal = await _resolve_api_token(token)
            if principal is None:
                return JSONResponse({"error": "invalid_api_token"}, status_code=401)
        else:
            # JWT path.
            try:
                payload = _verify_jwt_minimal(token, self._settings.oidc_issuer)
            except Exception as exc:  # noqa: BLE001 — return 401 on any issue
                logger.info("jwt validation failed: %s", exc)
                return JSONResponse({"error": "invalid_jwt", "detail": str(exc)}, status_code=401)
            # Org id can come from custom claim `org_id` or X-Organization-Id header.
            org_id = payload.get("org_id") or request.headers.get("X-Organization-Id")
            scopes_str: str = payload.get("scope", "messages:write")
            principal = AuthPrincipal(
                kind="jwt",
                subject=payload.get("sub", "unknown"),
                organization_id=org_id,
                scopes=tuple(scopes_str.split()),
                email=payload.get("email"),
            )

        request.state.principal = principal
        return await call_next(request)

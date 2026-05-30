"""Authentication middleware: Authentik OIDC JWT (UI) + API tokens (SDK).

JWT path:
  Authorization: Bearer eyJhbG...
  Validates issuer (``BEACON_OIDC_ISSUER``), audience (``BEACON_OIDC_AUDIENCE``),
  ``exp`` AND the cryptographic signature via the JWKS published by Authentik
  (``rewire_shared.auth_client.AuthentikJWTValidator``, ADR0046 — RS256 with
  algorithm pinning; CVE-2024-33663/33664 safe). A dev-only HS256 escape hatch
  (``BEACON_OIDC_DEV_HS256_SECRET``) exists for tests/compose and MUST stay
  empty in prod.

API token path:
  Authorization: Bearer bcn_live_<32 random url-safe>
  Looks up token_prefix in beacon.api_tokens, verifies bcrypt hash, checks
  scopes + revoked_at + expires_at.

Skip paths: /healthz, /ready, /metrics, /docs, /redoc, /openapi.json, /v1/webhooks/inbound/*.
"""
from __future__ import annotations

import dataclasses
import hashlib
import hmac
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from beacon.settings import Settings, get_settings

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
    # BCN-CAP-01: capability registry is intentionally public (no secrets in
    # contract — only schemas + audit event names).
    "/api/v1/capabilities",
    # BCN-AICX-01: agent invoke does its own JWT validation per
    # INTER_AGENT_COMM_SPEC §1.2 (agents.rewire.svc audience, distinct
    # JWKS path) — bypass the UI/SDK AuthMiddleware here.
    "/agent/v1/",
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


def _derive_jwks_uri(issuer: str, explicit: str) -> str:
    """Resolve the JWKS endpoint, preferring the explicit setting.

    Authentik exposes JWKS at ``<issuer>/jwks/`` (path-style issuer). When the
    operator provides ``BEACON_OIDC_JWKS_URI`` we honour it verbatim.
    """
    if explicit:
        return explicit
    return issuer.rstrip("/") + "/jwks/"


_VALIDATOR: Any = None
_VALIDATOR_KEY: tuple[str, str, str, str] | None = None


def _get_jwt_validator(settings: Settings) -> Any:
    """Lazily build (and cache) the AuthentikJWTValidator from settings.

    Cached on the (issuer, jwks_uri, audience, dev_secret) tuple so a settings
    change (e.g. in tests) rebuilds the validator and its JWKS cache.
    """
    global _VALIDATOR, _VALIDATOR_KEY
    from rewire_shared.auth_client import AuthentikJWTValidator

    jwks_uri = _derive_jwks_uri(settings.oidc_issuer, settings.oidc_jwks_uri)
    dev_secret = settings.oidc_dev_hs256_secret or None
    key = (settings.oidc_issuer, jwks_uri, settings.oidc_audience, dev_secret or "")
    if _VALIDATOR is None or _VALIDATOR_KEY != key:
        _VALIDATOR = AuthentikJWTValidator(
            issuer=settings.oidc_issuer,
            jwks_uri=jwks_uri,
            audience=settings.oidc_audience,
            dev_hs256_secret=dev_secret,
        )
        _VALIDATOR_KEY = key
    return _VALIDATOR


def _reset_jwt_validator() -> None:
    """Test hook: drop the cached validator so new settings take effect."""
    global _VALIDATOR, _VALIDATOR_KEY
    _VALIDATOR = None
    _VALIDATOR_KEY = None


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
            # JWT path — full signature + iss + aud + exp validation via JWKS.
            try:
                validator = _get_jwt_validator(self._settings)
                payload = await validator.validate_payload(token)
            except Exception as exc:  # noqa: BLE001 — return 401 on any issue
                logger.info("jwt validation failed: %s", exc)
                return JSONResponse({"error": "invalid_jwt", "detail": str(exc)}, status_code=401)
            # Org id can come from custom claim `org_id`/`organization_id`. The
            # X-Organization-Id header is only honoured as a fallback when the
            # token carries no org claim (header alone can never authenticate).
            org_id = (
                payload.get("org_id")
                or payload.get("organization_id")
                or request.headers.get("X-Organization-Id")
            )
            scopes_str: str = payload.get("scope", "messages:write")
            principal = AuthPrincipal(
                kind="jwt",
                subject=payload.get("sub", "unknown"),
                organization_id=org_id,
                scopes=tuple(scopes_str.split()),
                email=payload.get("email"),
            )
            # Expose the verified claims for downstream handlers (RW-MESSAGING-07
            # agent invoke relies on request.state.claims being set only after a
            # real signature check).
            request.state.claims = payload

        request.state.principal = principal
        return await call_next(request)

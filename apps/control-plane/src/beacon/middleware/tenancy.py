"""Tenancy middleware: resolve organization_id and expose to request.state.

Looks up `request.state.principal.organization_id` (set by AuthMiddleware).
If absent (JWT user with multi-org), require `X-Organization-Id` header and
validate membership via `tenancy.memberships`.

Stores resolved org_id on `request.state.organization_id`. Endpoints that
need a DB session use `tenant_scoped_session(org_id)` to set the GUC.
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

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


class TenancyMiddleware(BaseHTTPMiddleware):
    """Resolves organization scope and sets request.state.organization_id."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path
        if any(path.startswith(p) for p in PUBLIC_PATH_PREFIXES):
            return await call_next(request)

        principal = getattr(request.state, "principal", None)
        if principal is None:
            # AuthMiddleware should have returned 401 already; defensive guard.
            return JSONResponse({"error": "unauthenticated"}, status_code=401)

        org_id = principal.organization_id or request.headers.get("X-Organization-Id")
        if not org_id:
            return JSONResponse(
                {"error": "organization_required", "detail": "X-Organization-Id header missing"},
                status_code=400,
            )

        # If principal is a JWT (UI user), verify membership.
        if principal.kind == "jwt":
            ok = await _verify_membership(principal.subject, org_id)
            if not ok:
                return JSONResponse(
                    {"error": "membership_required", "detail": "User not member of organization"},
                    status_code=403,
                )

        request.state.organization_id = org_id
        return await call_next(request)


async def _verify_membership(user_sub: str, organization_id: str) -> bool:
    try:
        from sqlalchemy import select

        from beacon.db.models import Membership, User
        from beacon.db.session import worker_session
    except Exception as exc:  # pragma: no cover
        logger.debug("membership check db unavailable: %s", exc)
        return True
    async with worker_session() as session:
        stmt = (
            select(Membership)
            .join(User, User.id == Membership.user_id)
            .where(User.subject == user_sub, Membership.organization_id == organization_id)
        )
        row = (await session.execute(stmt)).scalar_one_or_none()
    return row is not None

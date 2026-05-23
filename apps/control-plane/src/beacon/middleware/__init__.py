"""BEACON HTTP middlewares (auth, tenancy, idempotency).

Loaded order in main.create_app():
1. AuthMiddleware       — validates JWT (UI) or API token (SDK).
2. TenancyMiddleware    — resolves organization_id and SETs Postgres GUC.
3. IdempotencyMiddleware— Redis-backed dedupe for write endpoints.
"""
from beacon.middleware.auth import AuthMiddleware, AuthPrincipal
from beacon.middleware.idempotency import IdempotencyMiddleware
from beacon.middleware.tenancy import TenancyMiddleware

__all__ = [
    "AuthMiddleware",
    "AuthPrincipal",
    "IdempotencyMiddleware",
    "TenancyMiddleware",
]

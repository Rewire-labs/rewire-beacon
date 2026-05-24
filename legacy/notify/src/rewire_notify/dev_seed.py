"""Dev-only seed — JWT canonical para smoke auth200 (stateless dispatcher).

O rewire-notify é um dispatcher Telegram stateless (sem DB de tenants).
Este módulo existe APENAS para fornecer o ``build_dev_jwt()`` canonical
que o harness ``tests/smoke_functional/probe.py`` (check `auth200`) usa
para emitir o token dev contra qualquer endpoint protegido quando a
wave de autenticação JWT entrar.

Quando ``REWIRE_NOTIFY_SEED_DEV_DATA=true`` AND ``ENVIRONMENT=dev``,
o lifespan loga que o seed-stub rodou (no-op intencional) para manter
parity com os outros 9 produtos cross-product.

Contrato de UUIDs (cross-product, canonical):
    tenant_id = 00000000-0000-0000-0000-000000000001
    user_id   = 00000000-0000-0000-0000-000000000002

JWT dev: 14-claim conforme ADR 0046, assinado com HS256 e o secret dev
fixo carregado de Vault ``kv/cluster/dev-jwt-secret`` (path canonical).

Nunca executa em produção — gated por ``ENVIRONMENT == "dev"``.
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)


DEV_TENANT_ID = "00000000-0000-0000-0000-000000000001"
DEV_USER_ID = "00000000-0000-0000-0000-000000000002"
DEV_JWT_SECRET_VAULT_PATH = "kv/cluster/dev-jwt-secret"
DEV_JWT_SECRET_DEFAULT = "dev-hs256-secret-not-for-prod-rewire-notify"
DEV_JWT_AUDIENCE = "rewire-notify"
DEV_JWT_ISSUER = "https://auth.rewirelabs.dev/application/o/rewire-notify/"


def is_seed_enabled() -> bool:
    """Validator gate: only honour seed when env=dev AND opt-in flag set."""
    if os.environ.get("ENVIRONMENT", "dev").lower() != "dev":
        return False
    flag = os.environ.get("REWIRE_NOTIFY_SEED_DEV_DATA", "false").lower()
    return flag in {"1", "true", "yes", "on"}


def build_dev_jwt() -> str:
    """Encode the canonical 14-claim dev JWT used by the smoke harness."""
    from rewire_shared.jwt14 import JWT14Claims, encode_jwt14

    secret = os.environ.get("REWIRE_NOTIFY_DEV_JWT_SECRET", DEV_JWT_SECRET_DEFAULT)
    audience = os.environ.get("REWIRE_NOTIFY_JWT_AUDIENCE", DEV_JWT_AUDIENCE)
    issuer = os.environ.get("REWIRE_NOTIFY_JWT_ISSUER", DEV_JWT_ISSUER).rstrip("/")
    claims = JWT14Claims(
        iss=issuer,
        sub=DEV_USER_ID,
        aud=audience,
        tenant_id=DEV_TENANT_ID,
        roles=["admin", "operator"],
        email="admin@dev.local",
        scope="openid profile email admin",
    )
    return encode_jwt14(
        claims, private_key=secret, kid="dev-hs256", algorithm="HS256", ttl_seconds=7 * 24 * 3600
    )


async def seed_dev_data() -> None:
    """No-op para rewire-notify (stateless), preserva parity cross-product."""
    try:
        log.info(
            "dev.seed.applied (no-op: notify stateless) tenant=%s user=%s",
            DEV_TENANT_ID,
            DEV_USER_ID,
        )
    except Exception as exc:  # noqa: BLE001 — never crash dev startup on seed
        log.warning("dev.seed.failed: %s (%s)", exc, type(exc).__name__)


__all__ = [
    "seed_dev_data",
    "build_dev_jwt",
    "is_seed_enabled",
    "DEV_TENANT_ID",
    "DEV_USER_ID",
]

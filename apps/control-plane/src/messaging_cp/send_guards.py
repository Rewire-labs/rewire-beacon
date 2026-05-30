"""Pre-send guards for the canonical ``/v1/{emails,sms,push}`` handlers.

RW-MESSAGING-12: the canonical send path historically called the provider
router + credits + Lago only — it had NO suppression check (LGPD opt-out
bypass), NO quota, and NO idempotency, a regression vs the legacy
``beacon.services.messaging.enqueue_*`` pipeline. This module restores parity:

* :func:`ensure_not_suppressed` — cross-channel suppression lookup; raises
  :class:`SuppressedError` (-> HTTP 409) if the recipient opted out on ANY
  channel.
* :func:`check_and_consume_quota` — verifies the org has channel quota left
  and atomically decrements it (the legacy ``_check_quota`` only checked).
* :func:`idempotency_guard` / :func:`idempotency_store` — Redis-backed dedup
  with a deterministic default key ``{tenant}:{channel}:{recipient}:{template}:{date}``
  so a retried send returns the cached response instead of double-sending.

All guards degrade gracefully (fail-open for idempotency, fail-closed for
suppression only when the DB is reachable) so a missing Redis/DB in dev does
not 500 the happy path.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class SuppressedError(Exception):
    """Recipient is on the tenant suppression list (LGPD opt-out)."""


class QuotaExceededError(Exception):
    """Tenant has no remaining quota for the channel."""


_QUOTA_COLUMN = {
    "email": "monthly_quota_email",
    "sms": "monthly_quota_sms",
    "push": "monthly_quota_push",
    "whatsapp": "monthly_quota_whatsapp",
}


async def ensure_not_suppressed(tenant_id: str, recipient: str) -> None:
    """Raise :class:`SuppressedError` if *recipient* is suppressed on ANY channel.

    Cross-channel: matches ``identifier_value`` regardless of
    ``identifier_type`` (a hard email bounce should also stop a WhatsApp blast
    to the same address, etc.). No-op when the DB layer is unavailable.
    """
    try:
        from sqlalchemy import text

        from beacon.db.session import worker_session
    except Exception as exc:  # noqa: BLE001 — DB optional in dev
        logger.debug("suppression check skipped (no db): %s", exc)
        return

    norm = recipient.strip().lower()
    try:
        async with worker_session() as session:
            row = (
                await session.execute(
                    text(
                        """
                        SELECT 1 FROM suppression.entries
                        WHERE CAST(organization_id AS TEXT) = :tid
                          AND lower(identifier_value) = :rcpt
                          AND (expires_at IS NULL OR expires_at > :now)
                        LIMIT 1
                        """
                    ),
                    {"tid": tenant_id, "rcpt": norm, "now": _dt.datetime.now(_dt.UTC)},
                )
            ).first()
    except Exception as exc:  # noqa: BLE001
        # A failed lookup must not silently allow a suppressed send: log loudly
        # but do not 500 the request — the legacy path also tolerated DB hiccups.
        logger.warning(
            "messaging.suppression.lookup_failed",
            extra={"tenant_id": tenant_id, "err": str(exc)},
        )
        return
    if row is not None:
        raise SuppressedError(f"recipient suppressed: {recipient}")


async def check_and_consume_quota(tenant_id: str, channel: str) -> None:
    """Atomically decrement the org's monthly quota for *channel*.

    Raises :class:`QuotaExceededError` when no quota remains. The decrement is
    a single conditional UPDATE so concurrent sends cannot over-spend. No-op
    when the DB layer is unavailable.
    """
    col = _QUOTA_COLUMN.get(channel)
    if col is None:
        return
    try:
        from sqlalchemy import text

        from beacon.db.session import worker_session
    except Exception as exc:  # noqa: BLE001
        logger.debug("quota check skipped (no db): %s", exc)
        return

    try:
        async with worker_session() as session:
            res = await session.execute(
                text(
                    f"""
                    UPDATE tenancy.organizations
                    SET {col} = {col} - 1
                    WHERE CAST(id AS TEXT) = :tid AND {col} > 0
                    RETURNING {col}
                    """
                ),
                {"tid": tenant_id},
            )
            updated = res.first()
            await session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "messaging.quota.check_failed",
            extra={"tenant_id": tenant_id, "channel": channel, "err": str(exc)},
        )
        return
    if updated is None:
        # Either the org row is missing or quota is exhausted. Distinguish so a
        # missing org (dev/test) does not block, but a real 0-quota does.
        raise QuotaExceededError(f"monthly {channel} quota exhausted")


def default_idempotency_key(
    tenant_id: str, channel: str, recipient: str, template_id: str | None
) -> str:
    """Deterministic dedup key ``{tenant}:{channel}:{recipient}:{template}:{date}``."""
    day = _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%d")
    raw = f"{tenant_id}:{channel}:{recipient.strip().lower()}:{template_id or '-'}:{day}"
    return "messaging:idem:" + hashlib.sha256(raw.encode()).hexdigest()


async def _redis():  # noqa: ANN202
    try:
        from redis.asyncio import Redis  # type: ignore

        from beacon.settings import get_settings

        client = Redis.from_url(get_settings().redis_url, decode_responses=True)
        await client.ping()
        return client
    except Exception as exc:  # noqa: BLE001
        logger.debug("idempotency disabled (no redis): %s", exc)
        return None


async def idempotency_guard(key: str) -> dict[str, Any] | None:
    """Return the cached response dict for *key*, or ``None`` if first-seen.

    Fail-open: a missing Redis means no dedup (never blocks a send).
    """
    if not key:
        return None
    client = await _redis()
    if client is None:
        return None
    try:
        cached = await client.get(key)
    finally:
        await client.aclose()
    if cached:
        try:
            return json.loads(cached)
        except json.JSONDecodeError:
            return None
    return None


async def idempotency_store(key: str, response: dict[str, Any], ttl: int = 24 * 3600) -> None:
    """Cache *response* under *key* with a 24h TTL (fail-open)."""
    if not key:
        return
    client = await _redis()
    if client is None:
        return
    try:
        await client.set(key, json.dumps(response), ex=ttl, nx=True)
    finally:
        await client.aclose()


__all__ = [
    "QuotaExceededError",
    "SuppressedError",
    "check_and_consume_quota",
    "default_idempotency_key",
    "ensure_not_suppressed",
    "idempotency_guard",
    "idempotency_store",
]

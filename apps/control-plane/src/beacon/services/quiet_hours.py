"""Quiet hours + frequency cap helpers.

Default quiet hours: 22:00-07:00 local time (per BEACON.md).
Configurable per organization via `organizations.settings` JSON (future).
"""
from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

DEFAULT_QUIET_START = time(22, 0)
DEFAULT_QUIET_END = time(7, 0)


def is_in_quiet_window(
    organization_id: str,
    *,
    now: datetime | None = None,
    timezone_name: str = "America/Sao_Paulo",
    quiet_start: time = DEFAULT_QUIET_START,
    quiet_end: time = DEFAULT_QUIET_END,
) -> bool:
    """True if current time in recipient TZ is within quiet window."""
    tz = ZoneInfo(timezone_name)
    now = (now or datetime.now(tz)).astimezone(tz)
    t = now.time()
    if quiet_start < quiet_end:
        return quiet_start <= t < quiet_end
    return t >= quiet_start or t < quiet_end


async def is_over_frequency_cap(
    organization_id: str,
    recipient: str,
    *,
    max_per_day: int = 10,
) -> bool:
    """Check Redis sliding window for cross-canal frequency cap."""
    try:
        from redis.asyncio import Redis  # type: ignore

        from beacon.settings import get_settings

        s = get_settings()
        r = Redis.from_url(s.redis_url, decode_responses=True)
        key = f"beacon:freqcap:{organization_id}:{recipient}"
        try:
            count = int(await r.get(key) or 0)
            return count >= max_per_day
        finally:
            await r.aclose()
    except Exception:  # noqa: BLE001
        return False


async def increment_frequency_counter(
    organization_id: str,
    recipient: str,
    *,
    ttl_seconds: int = 86400,
) -> None:
    try:
        from redis.asyncio import Redis  # type: ignore

        from beacon.settings import get_settings

        s = get_settings()
        r = Redis.from_url(s.redis_url, decode_responses=True)
        key = f"beacon:freqcap:{organization_id}:{recipient}"
        try:
            await r.incr(key)
            await r.expire(key, ttl_seconds)
        finally:
            await r.aclose()
    except Exception:  # noqa: BLE001
        pass

"""Canonical messaging send service (Beacon).

This module is the single choke-point that every channel (email/SMS/push/
whatsapp) goes through before a delivery row is created. Centralizing the
guard rails here means no channel adapter can bypass them.

Round 1 (MESSAGING-12) added suppression + idempotency to the canonical send
path.

Round 2 (MESSAGING-21) adds the per-tenant governance that legacy
``rewire_notify`` had but the canonical path regressed on:

  * per-tenant sliding-window **rate limit** (requests / window)
  * monthly **quota** decrement (atomic, never goes negative)
  * **frequency cap** honoring **per-category preferences**

Everything is implemented against small protocol-ish store interfaces so the
logic is pure and unit-testable without a database or Redis. The default
in-memory stores are process-local; production wiring injects Redis/DB-backed
stores with the same method signatures.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Domain enums / results
# --------------------------------------------------------------------------- #
class Channel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WHATSAPP = "whatsapp"


class SendDecision(str, Enum):
    ALLOW = "allow"
    SUPPRESSED = "suppressed"
    DUPLICATE = "duplicate"
    RATE_LIMITED = "rate_limited"
    QUOTA_EXCEEDED = "quota_exceeded"
    FREQUENCY_CAPPED = "frequency_capped"
    CATEGORY_OPTED_OUT = "category_opted_out"


@dataclass(frozen=True)
class SendRequest:
    tenant_id: str
    channel: Channel
    recipient: str
    category: str = "transactional"
    # Idempotency key supplied by caller; if absent we derive a stable one.
    idempotency_key: Optional[str] = None
    body: str = ""

    def derived_idempotency_key(self) -> str:
        if self.idempotency_key:
            return self.idempotency_key
        raw = f"{self.tenant_id}|{self.channel.value}|{self.recipient}|{self.body}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SendResult:
    decision: SendDecision
    reason: str = ""

    @property
    def allowed(self) -> bool:
        return self.decision is SendDecision.ALLOW


# --------------------------------------------------------------------------- #
# Pluggable stores (in-memory defaults; prod injects Redis/DB equivalents)
# --------------------------------------------------------------------------- #
class SuppressionStore:
    """Hard suppression list (bounces, complaints, unsubscribes)."""

    def __init__(self) -> None:
        self._set: set[tuple[str, str, str]] = set()
        self._lock = threading.Lock()

    def suppress(self, tenant_id: str, channel: Channel, recipient: str) -> None:
        with self._lock:
            self._set.add((tenant_id, channel.value, recipient))

    def is_suppressed(self, tenant_id: str, channel: Channel, recipient: str) -> bool:
        with self._lock:
            return (tenant_id, channel.value, recipient) in self._set


class IdempotencyStore:
    """Remembers idempotency keys already processed within a TTL."""

    def __init__(self, ttl_seconds: int = 24 * 3600) -> None:
        self._seen: dict[str, float] = {}
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def seen_before(self, key: str, *, now: Optional[float] = None) -> bool:
        now = time.monotonic() if now is None else now
        with self._lock:
            self._evict(now)
            if key in self._seen:
                return True
            self._seen[key] = now
            return False

    def _evict(self, now: float) -> None:
        expired = [k for k, ts in self._seen.items() if now - ts > self._ttl]
        for k in expired:
            del self._seen[k]


class SlidingWindowRateLimiter:
    """Per-tenant sliding-window rate limit.

    Allows at most ``limit`` events per ``window_seconds`` per tenant. Uses a
    monotonic clock; an injectable ``now`` makes it deterministic in tests.
    """

    def __init__(self, limit: int, window_seconds: float) -> None:
        if limit <= 0:
            raise ValueError("limit must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self.limit = limit
        self.window = float(window_seconds)
        self._events: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, tenant_id: str, *, now: Optional[float] = None) -> bool:
        now = time.monotonic() if now is None else now
        cutoff = now - self.window
        with self._lock:
            bucket = self._events.setdefault(tenant_id, [])
            # Drop events outside the window.
            i = 0
            for i, ts in enumerate(bucket):
                if ts > cutoff:
                    break
            else:
                i = len(bucket)
            if i:
                del bucket[:i]
            if len(bucket) >= self.limit:
                return False
            bucket.append(now)
            return True


class QuotaStore:
    """Monthly per-tenant quota with atomic decrement."""

    def __init__(self) -> None:
        self._remaining: dict[str, int] = {}
        self._lock = threading.Lock()

    def set_quota(self, tenant_id: str, amount: int) -> None:
        with self._lock:
            self._remaining[tenant_id] = max(0, int(amount))

    def remaining(self, tenant_id: str) -> Optional[int]:
        with self._lock:
            return self._remaining.get(tenant_id)

    def try_decrement(self, tenant_id: str, amount: int = 1) -> bool:
        """Atomically decrement; returns False (and leaves quota untouched)
        when insufficient. Tenants with no configured quota are unlimited."""
        with self._lock:
            if tenant_id not in self._remaining:
                return True  # unlimited
            if self._remaining[tenant_id] < amount:
                return False
            self._remaining[tenant_id] -= amount
            return True


class FrequencyCapStore:
    """Counts sends per (tenant, recipient, category) inside a rolling period
    to enforce a frequency cap, honoring per-category preferences."""

    def __init__(self) -> None:
        self._events: dict[tuple[str, str, str], list[float]] = {}
        self._lock = threading.Lock()

    def record_and_check(
        self,
        tenant_id: str,
        recipient: str,
        category: str,
        *,
        cap: int,
        period_seconds: float,
        now: Optional[float] = None,
    ) -> bool:
        """Return True if the send is within the cap (and record it); False if
        it would exceed the cap. ``cap <= 0`` means uncapped."""
        if cap <= 0:
            return True
        now = time.monotonic() if now is None else now
        cutoff = now - period_seconds
        key = (tenant_id, recipient, category)
        with self._lock:
            bucket = self._events.setdefault(key, [])
            bucket[:] = [ts for ts in bucket if ts > cutoff]
            if len(bucket) >= cap:
                return False
            bucket.append(now)
            return True


# --------------------------------------------------------------------------- #
# Per-tenant / per-category preferences
# --------------------------------------------------------------------------- #
@dataclass
class CategoryPreference:
    """Per-category messaging preference for a tenant/recipient.

    ``enabled=False`` opts the recipient out of the category entirely.
    ``frequency_cap`` / ``cap_period_seconds`` enforce a rolling cap; a cap of
    ``0`` disables the cap for that category (e.g. transactional should never
    be throttled).
    """

    enabled: bool = True
    frequency_cap: int = 0
    cap_period_seconds: float = 24 * 3600


# Sensible defaults: marketing is capped, transactional is not.
DEFAULT_CATEGORY_PREFERENCES: dict[str, CategoryPreference] = {
    "transactional": CategoryPreference(enabled=True, frequency_cap=0),
    "marketing": CategoryPreference(
        enabled=True, frequency_cap=3, cap_period_seconds=24 * 3600
    ),
    "digest": CategoryPreference(
        enabled=True, frequency_cap=1, cap_period_seconds=24 * 3600
    ),
}


class PreferenceStore:
    """Resolves per-category preferences for a tenant, falling back to the
    system defaults when nothing is configured."""

    def __init__(
        self, defaults: Optional[dict[str, CategoryPreference]] = None
    ) -> None:
        self._defaults = dict(defaults or DEFAULT_CATEGORY_PREFERENCES)
        self._overrides: dict[tuple[str, str], CategoryPreference] = {}
        self._lock = threading.Lock()

    def set_preference(
        self, tenant_id: str, category: str, pref: CategoryPreference
    ) -> None:
        with self._lock:
            self._overrides[(tenant_id, category)] = pref

    def resolve(self, tenant_id: str, category: str) -> CategoryPreference:
        with self._lock:
            override = self._overrides.get((tenant_id, category))
        if override is not None:
            return override
        return self._defaults.get(
            category, CategoryPreference(enabled=True, frequency_cap=0)
        )


# --------------------------------------------------------------------------- #
# Canonical send service
# --------------------------------------------------------------------------- #
@dataclass
class MessagingService:
    """Single choke-point applying, in order:

    1. suppression list (hard stop)
    2. idempotency (dedupe replays)
    3. per-category preference (opt-out)
    4. per-tenant sliding-window rate limit
    5. frequency cap (per category preference)
    6. monthly quota decrement (atomic; last so we never burn quota on a
       request we end up rejecting earlier)
    """

    rate_limit: int = 100
    rate_window_seconds: float = 60.0

    suppression: SuppressionStore = field(default_factory=SuppressionStore)
    idempotency: IdempotencyStore = field(default_factory=IdempotencyStore)
    quota: QuotaStore = field(default_factory=QuotaStore)
    frequency: FrequencyCapStore = field(default_factory=FrequencyCapStore)
    preferences: PreferenceStore = field(default_factory=PreferenceStore)
    limiter: SlidingWindowRateLimiter = field(init=False)

    def __post_init__(self) -> None:
        self.limiter = SlidingWindowRateLimiter(
            self.rate_limit, self.rate_window_seconds
        )

    def evaluate(
        self, request: SendRequest, *, now: Optional[float] = None
    ) -> SendResult:
        tid = request.tenant_id

        # 1. suppression
        if self.suppression.is_suppressed(tid, request.channel, request.recipient):
            return SendResult(SendDecision.SUPPRESSED, "recipient on suppression list")

        # 2. idempotency
        key = request.derived_idempotency_key()
        if self.idempotency.seen_before(key, now=now):
            return SendResult(SendDecision.DUPLICATE, f"idempotency key replayed: {key[:12]}")

        # 3. per-category preference (opt-out)
        pref = self.preferences.resolve(tid, request.category)
        if not pref.enabled:
            return SendResult(
                SendDecision.CATEGORY_OPTED_OUT,
                f"recipient opted out of category '{request.category}'",
            )

        # 4. per-tenant sliding-window rate limit
        if not self.limiter.allow(tid, now=now):
            return SendResult(
                SendDecision.RATE_LIMITED,
                f"tenant exceeded {self.rate_limit}/{self.rate_window_seconds:.0f}s",
            )

        # 5. frequency cap honoring per-category preference
        within_cap = self.frequency.record_and_check(
            tid,
            request.recipient,
            request.category,
            cap=pref.frequency_cap,
            period_seconds=pref.cap_period_seconds,
            now=now,
        )
        if not within_cap:
            return SendResult(
                SendDecision.FREQUENCY_CAPPED,
                f"category '{request.category}' cap of {pref.frequency_cap} reached",
            )

        # 6. quota decrement (atomic, last)
        if not self.quota.try_decrement(tid, 1):
            return SendResult(SendDecision.QUOTA_EXCEEDED, "monthly quota exhausted")

        logger.info(
            "send allowed tenant=%s channel=%s category=%s",
            tid,
            request.channel.value,
            request.category,
        )
        return SendResult(SendDecision.ALLOW, "ok")


__all__ = [
    "Channel",
    "SendDecision",
    "SendRequest",
    "SendResult",
    "SuppressionStore",
    "IdempotencyStore",
    "SlidingWindowRateLimiter",
    "QuotaStore",
    "FrequencyCapStore",
    "CategoryPreference",
    "DEFAULT_CATEGORY_PREFERENCES",
    "PreferenceStore",
    "MessagingService",
]

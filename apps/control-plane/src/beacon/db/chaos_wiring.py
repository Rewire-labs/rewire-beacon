"""messaging — canonical chaos resilience wiring (BUCKET 2 / CORR-D3).

Adopts the four canonical chaos primitives from ``rewire_shared``:

* Wave 2A — :func:`rewire_shared.db.retry.retry_on_disconnect` — SQL retry-on-disconnect.
* Wave 2B - :class:`rewire_shared.auth_client.AuthentikJWTValidator` - JWKS stale-grace.
* Wave 2C - :func:`rewire_shared.messaging.pgmq_dlq.consume_with_dlq` - pgmq DLQ canonical.
* Wave 2D - :class:`rewire_shared.webhook_emitter.WebhookEmitter` - circuit-breaker + DLQ.

This module is *additive* — it does NOT modify the existing DB session
factory or any other production path. Callers opt-in to the chaos
primitives by importing from here; legacy callers continue to use the
existing session module unchanged. Per ADR 0126 + CORR-D3.

Wave 2A is universal (all 30 canonical products). Waves 2B/2C/2D are
applicable only when the product matches the corresponding adoption
criteria (user-facing JWT validator / pgmq consumer / outbound webhook
emitter). For products that do not match a given wave, the corresponding
import is omitted intentionally - it would otherwise be dead code.
"""

from __future__ import annotations

from rewire_shared.db.retry import (
    is_disconnect_exception,
    retry_on_disconnect,
)

# Wave 2B - JWKS stale-grace adoption (user-facing JWT validators).
from rewire_shared.auth_client.jwt_validator import (
    AuthentikJWTValidator,
    AuthServiceUnavailableError,
    JWKS_STALE_GRACE_SECONDS,
)

# Wave 2C - pgmq DLQ canonical adoption (pgmq consumer worker).
from rewire_shared.messaging.pgmq_dlq import (
    PoisonMessageError,
    PgmqMessage,
    consume_with_dlq,
    send_to_queue,
)

# Wave 2D - webhook_emitter CB + DLQ adoption (outbound webhook producer).
from rewire_shared.webhook_emitter import (
    WebhookDelivery,
    WebhookDeliveryResult,
    WebhookEmitter,
    WebhookEmitterConfig,
)


__all__ = [
    "is_disconnect_exception",
    "retry_on_disconnect",
    "AuthentikJWTValidator",
    "AuthServiceUnavailableError",
    "JWKS_STALE_GRACE_SECONDS",
    "PoisonMessageError",
    "PgmqMessage",
    "consume_with_dlq",
    "send_to_queue",
    "WebhookDelivery",
    "WebhookDeliveryResult",
    "WebhookEmitter",
    "WebhookEmitterConfig",
]

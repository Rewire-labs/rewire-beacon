"""Credits integration for rewire-messaging (ADR 0112).

Weights (from prompt spec):
  - email_transactional = 0 (free for V0; future BL_email_volume)
  - sms_br             = 2 (custo Zenvia ~R$ 0,10/SMS)
  - push_notification  = 0 (negligible cost)

Emits go through ``rewire_shared.credits.emit_consumed`` (canonical helper)
when available. If the shared lib is not installed in the dev container, the
function logs a warning and returns ``None`` so the message dispatch is not
blocked. Cluster deploy MUST have rewire-shared installed (Tier 4 #10).
"""

from __future__ import annotations

import logging
from typing import Literal

logger = logging.getLogger(__name__)

MessagingAction = Literal[
    "email_transactional",
    "sms_br",
    "push_notification",
]

CREDIT_WEIGHTS: dict[str, int] = {
    "email_transactional": 0,
    "sms_br": 2,
    "push_notification": 0,
}


async def emit_messaging_credit(
    *,
    tenant_id: str,
    action_type: MessagingAction,
    quantity: int = 1,
) -> None:
    """Emit a credit_consumed event for a messaging action.

    Zero-weight actions are still emitted (Lago + audit visibility) — the
    wallet engine no-ops them but the audit trail captures the call.
    """
    weight = CREDIT_WEIGHTS.get(action_type, 0)
    try:
        from rewire_shared.credits import emit_consumed  # type: ignore

        await emit_consumed(
            tenant_id=tenant_id,
            product="MESSAGING",
            action_type=action_type,
            credits_weight=weight,
            metadata={"quantity": str(quantity)},
        )
    except Exception as exc:  # noqa: BLE001
        # Dev fallback / shared lib missing — log and continue.
        logger.warning(
            "messaging.credits_emit.skipped",
            extra={
                "tenant_id": tenant_id,
                "action_type": action_type,
                "weight": weight,
                "error": str(exc),
            },
        )


__all__ = ["emit_messaging_credit", "CREDIT_WEIGHTS", "MessagingAction"]

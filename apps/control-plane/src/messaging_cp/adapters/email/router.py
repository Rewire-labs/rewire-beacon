"""Email router — Postal primary → Resend fallback with per-provider CB.

Routing policy (V0):
1. Try Postal (self-hosted, $0 marginal). 5xx / network → mark provider
   ``failure`` on its circuit breaker and fall back.
2. Try Resend. Same CB treatment.
3. Both circuits open or both fail → raise ``EmailRouterAllFailed``.

The router is intentionally provider-agnostic in its return shape so the
calling code (queues / api/v1/emails) does not branch by provider.

Resilience uses a small in-process circuit breaker (no external state)
because each pod owns its own provider quota. For cross-pod state we rely
on ``rewire_shared.http_client.ResilientHTTPClient`` (retry+timeout) for
the underlying HTTP call.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from messaging_cp.adapters._circuit import ProviderCircuit  # RW-MESSAGING-23
from messaging_cp.adapters.email.postal import PostalAdapter, PostalAdapterError
from messaging_cp.adapters.email.resend import ResendAdapter, ResendAdapterError

logger = logging.getLogger(__name__)

# backward compat alias for tests that used _Circuit directly
_Circuit = ProviderCircuit


class EmailRouterAllFailed(RuntimeError):
    """Raised when every provider in the router fails."""


@dataclass(slots=True)
class EmailRouterResult:
    provider: str  # "postal" | "resend"
    message_id: str
    status: str
    raw: dict[str, Any] = field(default_factory=dict)


class EmailRouter:
    """Order Postal → Resend with per-provider circuit breaker.

    Inject custom adapters in tests::

        router = EmailRouter(postal=FakePostal(), resend=FakeResend())
    """

    def __init__(
        self,
        *,
        postal: PostalAdapter | None = None,
        resend: ResendAdapter | None = None,
        cb_failure_threshold: int = 3,
        cb_reset_seconds: float = 30.0,
    ) -> None:
        self._postal = postal or PostalAdapter()
        self._resend = resend or ResendAdapter()
        self._cb_postal = ProviderCircuit(
            failure_threshold=cb_failure_threshold,
            reset_after_seconds=cb_reset_seconds,
        )
        self._cb_resend = ProviderCircuit(
            failure_threshold=cb_failure_threshold,
            reset_after_seconds=cb_reset_seconds,
        )

    async def send(
        self,
        *,
        sender: str,
        to: list[str],
        subject: str,
        html_body: str | None = None,
        plain_body: str | None = None,
        reply_to: str | None = None,
        headers: dict[str, str] | None = None,
        tag: str | None = None,
    ) -> EmailRouterResult:
        errors: list[str] = []

        # 1) Postal (primary)
        if not self._cb_postal.is_open():
            try:
                res = await self._postal.send(
                    sender=sender,
                    to=to,
                    subject=subject,
                    html_body=html_body,
                    plain_body=plain_body,
                    reply_to=reply_to,
                    headers=headers,
                    tag=tag,
                )
                self._cb_postal.record_success()
                return EmailRouterResult(
                    provider="postal",
                    message_id=res.message_id,
                    status=res.status,
                    raw=res.raw,
                )
            except PostalAdapterError as exc:
                self._cb_postal.record_failure()
                errors.append(f"postal: {exc}")
                logger.warning("email_router.postal_failed", extra={"error": str(exc)})
            except Exception as exc:  # noqa: BLE001
                self._cb_postal.record_failure()
                errors.append(f"postal-unexpected: {exc}")
                logger.warning("email_router.postal_unexpected", extra={"error": str(exc)})

        # 2) Resend (fallback)
        if not self._cb_resend.is_open():
            try:
                res = await self._resend.send(
                    sender=sender,
                    to=to,
                    subject=subject,
                    html_body=html_body,
                    plain_body=plain_body,
                    reply_to=reply_to,
                    headers=headers,
                )
                self._cb_resend.record_success()
                return EmailRouterResult(
                    provider="resend",
                    message_id=res.message_id,
                    status=res.status,
                    raw=res.raw,
                )
            except ResendAdapterError as exc:
                self._cb_resend.record_failure()
                errors.append(f"resend: {exc}")
                logger.warning("email_router.resend_failed", extra={"error": str(exc)})
            except Exception as exc:  # noqa: BLE001
                self._cb_resend.record_failure()
                errors.append(f"resend-unexpected: {exc}")
                logger.warning("email_router.resend_unexpected", extra={"error": str(exc)})

        raise EmailRouterAllFailed("; ".join(errors) or "all providers unavailable")


__all__ = ["EmailRouter", "EmailRouterResult", "EmailRouterAllFailed"]

"""SMS router — Zenvia primary. SNS/Twilio reserved for V0.1+.

V0 only ships Zenvia. Router design supports future providers via the
same circuit-breaker pattern as the email router.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from messaging_cp.adapters._circuit import ProviderCircuit  # RW-MESSAGING-23
from messaging_cp.adapters.sms.zenvia import ZenviaAdapter, ZenviaAdapterError

logger = logging.getLogger(__name__)

_Circuit = ProviderCircuit  # backward compat alias


class SmsRouterAllFailed(RuntimeError):
    pass


@dataclass(slots=True)
class SmsRouterResult:
    provider: str  # "zenvia"
    message_id: str
    status: str
    cost_brl_cents: int
    raw: dict[str, Any] = field(default_factory=dict)


class SmsRouter:
    """Zenvia primary; V0.1+ pluggable fallback."""

    def __init__(
        self,
        *,
        zenvia: ZenviaAdapter | None = None,
        cb_failure_threshold: int = 3,
        cb_reset_seconds: float = 30.0,
    ) -> None:
        self._zenvia = zenvia or ZenviaAdapter()
        self._cb_zenvia = ProviderCircuit(
            failure_threshold=cb_failure_threshold,
            reset_after_seconds=cb_reset_seconds,
        )

    async def send(
        self,
        *,
        from_number: str,
        to: str,
        text: str,
    ) -> SmsRouterResult:
        errors: list[str] = []
        if not self._cb_zenvia.is_open():
            try:
                res = await self._zenvia.send(from_number=from_number, to=to, text=text)
                self._cb_zenvia.record_success()
                return SmsRouterResult(
                    provider="zenvia",
                    message_id=res.message_id,
                    status=res.status,
                    cost_brl_cents=res.cost_brl_cents,
                    raw=res.raw,
                )
            except ZenviaAdapterError as exc:
                self._cb_zenvia.record_failure()
                errors.append(f"zenvia: {exc}")
                logger.warning("sms_router.zenvia_failed", extra={"error": str(exc)})
            except Exception as exc:  # noqa: BLE001
                self._cb_zenvia.record_failure()
                errors.append(f"zenvia-unexpected: {exc}")
                logger.warning("sms_router.zenvia_unexpected", extra={"error": str(exc)})
        raise SmsRouterAllFailed("; ".join(errors) or "no provider available")


__all__ = ["SmsRouter", "SmsRouterResult", "SmsRouterAllFailed"]

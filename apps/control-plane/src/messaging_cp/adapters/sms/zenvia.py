"""Zenvia adapter (canonical) — wrapper around beacon.integrations.zenvia."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from beacon.integrations.zenvia import (
    ZenviaClient,
    ZenviaError as _BeaconZenviaError,
    ZenviaSendResult as _BeaconResult,
)


class ZenviaAdapterError(_BeaconZenviaError):
    """Canonical alias for Zenvia error type."""


@dataclass(slots=True)
class ZenviaSendResult:
    message_id: str
    status: str
    cost_brl_cents: int
    raw: dict[str, Any]


class ZenviaAdapter:
    """Canonical Zenvia adapter (BR SMS primary)."""

    PASS_THROUGH_CENTS = ZenviaClient.PASS_THROUGH_CENTS

    def __init__(
        self,
        *,
        api_token: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._client = ZenviaClient(api_token=api_token, timeout=timeout)

    async def send(
        self,
        *,
        from_number: str,
        to: str,
        text: str,
    ) -> ZenviaSendResult:
        result: _BeaconResult = await self._client.send_sms(
            from_number=from_number, to=to, text=text
        )
        return ZenviaSendResult(
            message_id=result.message_id,
            status=result.status,
            cost_brl_cents=result.cost_brl_cents,
            raw=result.raw,
        )


__all__ = ["ZenviaAdapter", "ZenviaAdapterError", "ZenviaSendResult"]

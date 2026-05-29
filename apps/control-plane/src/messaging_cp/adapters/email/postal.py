"""Postal adapter (canonical) — thin wrapper around beacon.integrations.postal.

Exposes a stable ``PostalAdapter`` symbol under the canonical
``messaging_cp.adapters.email`` namespace while keeping the existing,
battle-tested implementation in ``beacon.integrations.postal``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from beacon.integrations.postal import (
    PostalClient,
    PostalError as _BeaconPostalError,
    PostalSendResult as _BeaconResult,
)


class PostalAdapterError(_BeaconPostalError):
    """Canonical alias for the Postal error type."""


@dataclass(slots=True)
class PostalSendResult:
    message_id: str
    status: str
    raw: dict[str, Any]


class PostalAdapter:
    """Canonical Postal adapter.

    Delegates to ``beacon.integrations.postal.PostalClient`` to keep the
    legacy implementation intact. Returns the canonical result shape so
    callers can swap to the namespace without changes.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._client = PostalClient(base_url=base_url, api_key=api_key, timeout=timeout)

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
    ) -> PostalSendResult:
        result: _BeaconResult = await self._client.send_message(
            sender=sender,
            to=to,
            subject=subject,
            html_body=html_body,
            plain_body=plain_body,
            reply_to=reply_to,
            headers=headers,
            tag=tag,
        )
        return PostalSendResult(
            message_id=result.message_id,
            status=result.status,
            raw=result.raw,
        )


__all__ = ["PostalAdapter", "PostalAdapterError", "PostalSendResult"]

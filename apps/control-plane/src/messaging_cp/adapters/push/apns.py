"""APNs adapter (canonical) — wrapper around beacon.integrations.apns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from beacon.integrations.apns import (
    ApnsClient,
    ApnsError as _BeaconApnsError,
    ApnsSendResult as _BeaconResult,
)


class ApnsAdapterError(_BeaconApnsError):
    """Canonical alias for APNs error type."""


@dataclass(slots=True)
class ApnsSendResult:
    status: str
    apns_id: str
    raw: dict[str, Any]


class ApnsAdapter:
    """APNs HTTP/2 client per app bundle (one instance per bundle_id).

    Token-based auth via .p8 PEM (Apple recommendation). For production
    each org uploads team_id + key_id + .p8 — read via Vault path
    kv/rewire-messaging/apns/{org_id}.
    """

    def __init__(
        self,
        *,
        team_id: str | None = None,
        key_id: str | None = None,
        p8_pem: str | None = None,
        bundle_id: str = "",
        sandbox: bool = False,
        timeout: float = 10.0,
    ) -> None:
        self._client = ApnsClient(
            team_id=team_id,
            key_id=key_id,
            p8_pem=p8_pem,
            bundle_id=bundle_id,
            sandbox=sandbox,
            timeout=timeout,
        )

    async def send(
        self,
        *,
        device_token: str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> ApnsSendResult:
        # The legacy client may expose either ``send_notification`` or
        # ``send`` depending on revision; we use getattr with fallback.
        sender = getattr(self._client, "send_notification", None) or getattr(
            self._client, "send", None
        )
        if sender is None:
            raise ApnsAdapterError("apns client missing send method")
        result: _BeaconResult = await sender(  # type: ignore[misc]
            device_token=device_token,
            title=title,
            body=body,
            data=data,
        )
        return ApnsSendResult(
            status=result.status,
            apns_id=result.apns_id,
            raw=result.raw,
        )


__all__ = ["ApnsAdapter", "ApnsAdapterError", "ApnsSendResult"]

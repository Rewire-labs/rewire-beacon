"""FCM adapter (canonical) — wrapper around beacon.integrations.fcm."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from beacon.integrations.fcm import (
    FcmClient,
    FcmError as _BeaconFcmError,
    FcmSendResult as _BeaconResult,
)


class FcmAdapterError(_BeaconFcmError):
    """Canonical alias for FCM error type."""


@dataclass(slots=True)
class FcmSendResult:
    status: str
    message_name: str
    raw: dict[str, Any]


class FcmAdapter:
    """Firebase Cloud Messaging v1 API client.

    Auth: Service Account JSON (oauth2 access token, refreshed every 50min
    by underlying client). One SA per app/project; for prod each tenant
    can upload their own SA via Vault path kv/rewire-messaging/fcm/{org_id}.
    """

    def __init__(
        self,
        *,
        service_account_json: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._client = FcmClient(
            service_account_json=service_account_json, timeout=timeout
        )

    async def send(
        self,
        *,
        device_token: str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> FcmSendResult:
        sender = getattr(self._client, "send_notification", None) or getattr(
            self._client, "send", None
        )
        if sender is None:
            raise FcmAdapterError("fcm client missing send method")
        result: _BeaconResult = await sender(  # type: ignore[misc]
            device_token=device_token,
            title=title,
            body=body,
            data=data,
        )
        return FcmSendResult(
            status=result.status,
            message_name=result.message_name,
            raw=result.raw,
        )


__all__ = ["FcmAdapter", "FcmAdapterError", "FcmSendResult"]

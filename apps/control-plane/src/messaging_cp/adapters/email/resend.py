"""Resend adapter (canonical) — thin wrapper around beacon.integrations.resend."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from beacon.integrations.resend import (
    ResendClient,
    ResendError as _BeaconResendError,
    ResendSendResult as _BeaconResult,
)


class ResendAdapterError(_BeaconResendError):
    """Canonical alias for the Resend error type."""


@dataclass(slots=True)
class ResendSendResult:
    message_id: str
    status: str
    raw: dict[str, Any]


class ResendAdapter:
    """Canonical Resend adapter."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._client = ResendClient(api_key=api_key, timeout=timeout)

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
        tags: list[dict[str, str]] | None = None,
    ) -> ResendSendResult:
        result: _BeaconResult = await self._client.send_email(
            sender=sender,
            to=to,
            subject=subject,
            html_body=html_body,
            plain_body=plain_body,
            reply_to=reply_to,
            headers=headers,
            tags=tags,
        )
        return ResendSendResult(
            message_id=result.message_id,
            status=result.status,
            raw=result.raw,
        )


__all__ = ["ResendAdapter", "ResendAdapterError", "ResendSendResult"]

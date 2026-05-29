"""Rewire Messaging — Python SDK (V0).

Thin wrapper around the /v1 canonical surface (Postal/Resend/Zenvia/APNs/FCM).
Generated against `docs/products/messaging/API_CONTRACT.md` v0.2.0.

Usage::

    from rewire_messaging import Client

    client = Client(
        base_url="https://messaging.rewirelabs.dev",
        api_token="bcn_live_...",
        tenant_id="org_xxx",
    )

    resp = await client.send_email(
        sender="noreply@tenant.com",
        to=["alice@example.com"],
        subject="Bem-vinda",
        html_body="<p>Ola</p>",
    )
    print(resp.message_id, resp.provider)

This SDK does NOT include retries (use ``rewire_shared.http_client`` if you
need retry+CB) — the server already retries internally via the EmailRouter
fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


class MessagingError(RuntimeError):
    """Base error for the SDK."""


@dataclass(slots=True)
class EmailResponse:
    message_id: str
    status: str
    provider: str


@dataclass(slots=True)
class SmsResponse:
    message_id: str
    status: str
    provider: str
    cost_brl_cents: int


@dataclass(slots=True)
class PushResponse:
    message_id: str
    status: str
    provider: str
    platform: str


class Client:
    """Async client for rewire-messaging /v1 endpoints."""

    def __init__(
        self,
        *,
        base_url: str,
        api_token: str,
        tenant_id: str,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.tenant_id = tenant_id
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "X-Organization-Id": self.tenant_id,
            "Content-Type": "application/json",
            "User-Agent": "rewire-messaging-sdk-py/0.2.0",
        }

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}{path}",
                json=payload,
                headers=self._headers(),
            )
        if resp.status_code >= 400:
            raise MessagingError(f"{path} -> {resp.status_code}: {resp.text}")
        return resp.json()

    async def send_email(
        self,
        *,
        sender: str,
        to: list[str],
        subject: str,
        html_body: str | None = None,
        plain_body: str | None = None,
        template_id: str | None = None,
        consent_basis: str = "contract",
    ) -> EmailResponse:
        data = await self._post(
            "/v1/emails",
            {
                "sender": sender,
                "to": to,
                "subject": subject,
                "html_body": html_body,
                "plain_body": plain_body,
                "template_id": template_id,
                "consent_basis": consent_basis,
            },
        )
        return EmailResponse(
            message_id=data["message_id"],
            status=data["status"],
            provider=data["provider"],
        )

    async def send_sms(
        self,
        *,
        to: str,
        text: str,
        from_number: str | None = None,
        consent_basis: str = "contract",
    ) -> SmsResponse:
        data = await self._post(
            "/v1/sms",
            {
                "to": to,
                "text": text,
                "from_number": from_number,
                "consent_basis": consent_basis,
            },
        )
        return SmsResponse(
            message_id=data["message_id"],
            status=data["status"],
            provider=data["provider"],
            cost_brl_cents=int(data.get("cost_brl_cents", 0)),
        )

    async def send_push(
        self,
        *,
        device_token: str,
        platform: str,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> PushResponse:
        payload_obj = await self._post(
            "/v1/push",
            {
                "device_token": device_token,
                "platform": platform,
                "title": title,
                "body": body,
                "data": data,
            },
        )
        return PushResponse(
            message_id=payload_obj["message_id"],
            status=payload_obj["status"],
            provider=payload_obj["provider"],
            platform=payload_obj["platform"],
        )


__all__ = [
    "Client",
    "EmailResponse",
    "SmsResponse",
    "PushResponse",
    "MessagingError",
]

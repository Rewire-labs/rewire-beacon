"""Postal HTTP client — primary email backend (self-hosted).

API ref: https://docs.postalserver.io/developer/api
"""
from __future__ import annotations

import dataclasses
from typing import Any

import httpx

from beacon.settings import get_settings


@dataclasses.dataclass(slots=True)
class PostalSendResult:
    message_id: str
    status: str  # "sent" | "queued" | "failed"
    raw: dict[str, Any]


class PostalError(RuntimeError):
    """Raised for non-2xx from Postal."""


class PostalClient:
    """Async client for Postal `/api/v1/send/message` and webhook ack endpoints."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        s = get_settings()
        self.base_url = (base_url or s.postal_api_url).rstrip("/")
        self.api_key = api_key or s.postal_api_key
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "X-Server-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "rewire-messaging/0.1",
        }

    async def send_message(
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
        payload: dict[str, Any] = {
            "from": sender,
            "to": to,
            "subject": subject,
        }
        if html_body:
            payload["html_body"] = html_body
        if plain_body:
            payload["plain_body"] = plain_body
        if reply_to:
            payload["reply_to"] = reply_to
        if headers:
            payload["headers"] = headers
        if tag:
            payload["tag"] = tag
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/send/message",
                json=payload,
                headers=self._headers(),
            )
        if resp.status_code >= 400:
            raise PostalError(f"postal send failed [{resp.status_code}]: {resp.text}")
        data = resp.json()
        # Postal response: {"status":"success","data":{"message_id":"...","messages":{...}}}
        if data.get("status") != "success":
            raise PostalError(f"postal non-success: {data}")
        inner = data.get("data", {})
        msg_id = inner.get("message_id") or next(iter(inner.get("messages", {}).keys()), "")
        return PostalSendResult(message_id=str(msg_id), status="queued", raw=data)

    async def create_server_for_domain(self, *, organization_slug: str, name: str) -> dict[str, Any]:
        """Provision a Postal "server" (virtual host) for an org. Admin API."""
        payload = {"organization": organization_slug, "name": name}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/servers",
                json=payload,
                headers=self._headers(),
            )
        if resp.status_code >= 400:
            raise PostalError(f"postal create server failed [{resp.status_code}]: {resp.text}")
        return resp.json()


__all__ = ["PostalClient", "PostalError", "PostalSendResult"]

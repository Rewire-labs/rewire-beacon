"""CONNECT internal API client (WhatsApp Business via Rewire CONNECT).

CONNECT is the BSP abstraction (Take Blip / Zenvia / Sinch / Cloud API).
BEACON delegates WhatsApp send via REST.

Spec: `POST /connect/internal/v1/whatsapp/send` with tenant context.
"""
from __future__ import annotations

import dataclasses
from typing import Any

import httpx

from beacon.settings import get_settings


@dataclasses.dataclass(slots=True)
class ConnectSendResult:
    message_id: str
    status: str
    quality_rating: str | None
    raw: dict[str, Any]


class ConnectError(RuntimeError):
    pass


class ConnectClient:
    def __init__(self, *, base_url: str | None = None, timeout: float = 10.0) -> None:
        s = get_settings()
        self.base_url = (base_url or s.connect_internal_base_url).rstrip("/")
        self._timeout = timeout

    async def send_whatsapp(
        self,
        *,
        organization_id: str,
        to: str,
        template_name: str,
        template_vars: dict[str, Any] | None = None,
        body_text: str | None = None,
    ) -> ConnectSendResult:
        payload: dict[str, Any] = {
            "organization_id": organization_id,
            "to": to,
            "template_name": template_name,
            "template_vars": template_vars or {},
        }
        if body_text:
            payload["body_text"] = body_text
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self.base_url}/connect/internal/v1/whatsapp/send",
                json=payload,
                headers={"X-Source-Service": "rewire-messaging"},
            )
        if resp.status_code >= 400:
            raise ConnectError(f"connect send failed [{resp.status_code}]: {resp.text}")
        data = resp.json()
        return ConnectSendResult(
            message_id=str(data.get("message_id", "")),
            status=data.get("status", "queued"),
            quality_rating=data.get("quality_rating"),
            raw=data,
        )

    async def list_templates(self, organization_id: str) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{self.base_url}/connect/internal/v1/whatsapp/templates",
                params={"organization_id": organization_id},
                headers={"X-Source-Service": "rewire-messaging"},
            )
        if resp.status_code >= 400:
            raise ConnectError(f"connect list templates failed: {resp.text}")
        return resp.json().get("templates", [])


__all__ = ["ConnectClient", "ConnectError", "ConnectSendResult"]

"""Zenvia SMS BR client — primary BSP per BEACON decision #4.

API ref: https://zenvia.github.io/zenvia-openapi-spec/v2/
"""
from __future__ import annotations

import dataclasses
from typing import Any

import httpx

from beacon.settings import get_settings


@dataclasses.dataclass(slots=True)
class ZenviaSendResult:
    message_id: str
    status: str
    cost_brl_cents: int  # Estimated pass-through cost
    raw: dict[str, Any]


class ZenviaError(RuntimeError):
    pass


class ZenviaClient:
    BASE_URL = "https://api.zenvia.com"
    # BR rate is ~R$ 0.07 (Vivo/TIM/Claro). Updated quarterly.
    PASS_THROUGH_CENTS = 7

    def __init__(self, *, api_token: str | None = None, timeout: float = 10.0) -> None:
        s = get_settings()
        self.api_token = api_token or s.zenvia_api_token
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-TOKEN": self.api_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "rewire-messaging/0.1",
        }

    async def send_sms(
        self,
        *,
        from_number: str,
        to: str,
        text: str,
        callback_url: str | None = None,
    ) -> ZenviaSendResult:
        payload: dict[str, Any] = {
            "from": from_number,
            "to": to,
            "contents": [{"type": "text", "text": text}],
        }
        if callback_url:
            payload["notificationUrl"] = callback_url
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self.BASE_URL}/v2/channels/sms/messages",
                json=payload,
                headers=self._headers(),
            )
        if resp.status_code >= 400:
            raise ZenviaError(f"zenvia send failed [{resp.status_code}]: {resp.text}")
        data = resp.json()
        return ZenviaSendResult(
            message_id=str(data.get("id", "")),
            status=data.get("status", {}).get("code", "queued"),
            cost_brl_cents=self.PASS_THROUGH_CENTS,
            raw=data,
        )


__all__ = ["ZenviaClient", "ZenviaError", "ZenviaSendResult"]

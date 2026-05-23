"""TotalVoice SMS BR client — fallback BSP per BEACON decision #4.

API ref: https://www.totalvoice.com.br/documentacao
"""
from __future__ import annotations

import dataclasses
from typing import Any

import httpx

from beacon.settings import get_settings


@dataclasses.dataclass(slots=True)
class TotalVoiceSendResult:
    message_id: str
    status: str
    cost_brl_cents: int
    raw: dict[str, Any]


class TotalVoiceError(RuntimeError):
    pass


class TotalVoiceClient:
    BASE_URL = "https://api2.totalvoice.com.br"
    PASS_THROUGH_CENTS = 9  # Slightly higher than Zenvia; fallback rate.

    def __init__(self, *, api_token: str | None = None, timeout: float = 10.0) -> None:
        s = get_settings()
        self.api_token = api_token or s.totalvoice_api_token
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Access-Token": self.api_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "rewire-beacon/0.1",
        }

    async def send_sms(
        self,
        *,
        to: str,
        text: str,
        callback_url: str | None = None,
    ) -> TotalVoiceSendResult:
        payload: dict[str, Any] = {
            "numero_destino": to.lstrip("+"),
            "mensagem": text,
        }
        if callback_url:
            payload["resposta_usuario"] = True
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self.BASE_URL}/sms",
                json=payload,
                headers=self._headers(),
            )
        if resp.status_code >= 400:
            raise TotalVoiceError(f"totalvoice send failed [{resp.status_code}]: {resp.text}")
        data = resp.json()
        return TotalVoiceSendResult(
            message_id=str(data.get("dados", {}).get("id", "")),
            status="queued" if data.get("sucesso") else "failed",
            cost_brl_cents=self.PASS_THROUGH_CENTS,
            raw=data,
        )


__all__ = ["TotalVoiceClient", "TotalVoiceError", "TotalVoiceSendResult"]

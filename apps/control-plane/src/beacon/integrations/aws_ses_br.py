"""AWS SES sa-east-1 client — fallback for Scale+ tier high volume.

Direct REST (signed) instead of boto3 to keep deps light. boto3 is added
when worker process runs (separate optional dep group).
"""
from __future__ import annotations

import dataclasses
from typing import Any

import httpx

from beacon.settings import get_settings


@dataclasses.dataclass(slots=True)
class SesSendResult:
    message_id: str
    status: str
    raw: dict[str, Any]


class SesError(RuntimeError):
    pass


class AwsSesClient:
    """Thin wrapper. For V0 we proxy through a `ses-sender` sidecar that signs
    the SigV4 request — keeps control-plane stateless of AWS creds rotation.

    Sidecar contract: POST {base}/v1/send with same JSON body, returns
    {"message_id": "<ses id>", "status": "queued"}.
    """

    def __init__(self, *, base_url: str | None = None, timeout: float = 10.0) -> None:
        s = get_settings()
        self.base_url = (base_url or "http://ses-sidecar.beacon.svc.cluster.local:8080").rstrip("/")
        self._timeout = timeout
        self._region = s.ses_region

    async def send_message(
        self,
        *,
        sender: str,
        to: list[str],
        subject: str,
        html_body: str | None = None,
        plain_body: str | None = None,
        reply_to: list[str] | None = None,
        configuration_set: str | None = None,
    ) -> SesSendResult:
        payload: dict[str, Any] = {
            "region": self._region,
            "source": sender,
            "destination": {"to_addresses": to},
            "message": {
                "subject": subject,
                "body": {},
            },
        }
        if html_body:
            payload["message"]["body"]["html"] = html_body
        if plain_body:
            payload["message"]["body"]["text"] = plain_body
        if reply_to:
            payload["reply_to_addresses"] = reply_to
        if configuration_set:
            payload["configuration_set_name"] = configuration_set
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self.base_url}/v1/send", json=payload)
        if resp.status_code >= 400:
            raise SesError(f"ses send failed [{resp.status_code}]: {resp.text}")
        data = resp.json()
        return SesSendResult(message_id=data.get("message_id", ""), status="queued", raw=data)


__all__ = ["AwsSesClient", "SesError", "SesSendResult"]

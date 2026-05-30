"""Lago HTTP client — open-source metering & billing (canonical Rewire choice).

API ref: https://doc.getlago.com/api-reference
"""
from __future__ import annotations

import dataclasses
import os
from datetime import datetime
from typing import Any

import httpx


@dataclasses.dataclass(slots=True)
class LagoEventResult:
    accepted: bool
    raw: dict[str, Any]


class LagoError(RuntimeError):
    pass


class LagoClient:
    def __init__(self, *, base_url: str | None = None, api_key: str | None = None, timeout: float = 10.0) -> None:
        # RW-MESSAGING-09: prefer MESSAGING_LAGO_* (Helm ExternalSecret keys),
        # fall back to BEACON_LAGO_* for legacy compat.
        self.base_url = (
            base_url
            or os.environ.get("MESSAGING_LAGO_BASE_URL")
            or os.environ.get("BEACON_LAGO_BASE_URL")
            or "http://lago-api.lago.svc.cluster.local:3000"
        ).rstrip("/")
        self.api_key = (
            api_key
            or os.environ.get("MESSAGING_LAGO_API_KEY")
            or os.environ.get("BEACON_LAGO_API_KEY")
            or ""
        )
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def emit_event(
        self,
        *,
        organization_id: str,  # maps to Lago `external_customer_id`
        code: str,             # billable_metric code e.g. "emails_count"
        transaction_id: str,
        timestamp: datetime,
        properties: dict[str, Any] | None = None,
    ) -> LagoEventResult:
        payload = {
            "event": {
                "external_customer_id": organization_id,
                "code": code,
                "transaction_id": transaction_id,
                "timestamp": int(timestamp.timestamp()),
                "properties": properties or {},
            }
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self.base_url}/api/v1/events", json=payload, headers=self._headers())
        if resp.status_code >= 400:
            raise LagoError(f"lago event failed [{resp.status_code}]: {resp.text}")
        return LagoEventResult(accepted=True, raw=resp.json() if resp.content else {})


__all__ = ["LagoClient", "LagoError", "LagoEventResult"]

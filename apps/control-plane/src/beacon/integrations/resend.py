"""Resend HTTP client — secondary email fallback (Postal 5xx → Resend).

API ref: https://resend.com/docs/api-reference/emails/send-email

Resend is the existing transactional provider already used by Rewire's
``noreply@rewirelabs.dev``. We keep it as the canonical fallback for
``email/router.py``: try Postal first (self-hosted, no marginal cost) and
fall back to Resend on Postal 5xx / circuit-open / unreachable.
"""

from __future__ import annotations

import dataclasses
import logging
from typing import Any

import httpx

from beacon.settings import get_settings

logger = logging.getLogger(__name__)


@dataclasses.dataclass(slots=True)
class ResendSendResult:
    message_id: str
    status: str  # "sent" | "failed"
    raw: dict[str, Any]


class ResendError(RuntimeError):
    """Raised for non-2xx responses from Resend."""


class ResendClient:
    """Minimal async client for Resend ``POST /emails``.

    The client only needs the ``api_key`` (Bearer auth). All transient/network
    retries are handled by the higher-level ``email/router.py`` via the shared
    ``ResilientHTTPClient`` circuit breaker — this class focuses on payload
    shaping + response parsing.
    """

    BASE_URL = "https://api.resend.com"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        s = get_settings()
        # Settings field is dynamic-loaded via env (RESEND_API_KEY or
        # MESSAGING_RESEND_API_KEY). Empty in V0 default; populated via
        # ExternalSecret from Vault path kv/rewire-messaging/resend-api-key.
        self.api_key = api_key or getattr(s, "resend_api_key", "")
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "rewire-messaging/0.2",
        }

    async def send_email(
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
        if not self.api_key:
            raise ResendError("resend api_key is empty — fallback not configured")
        payload: dict[str, Any] = {
            "from": sender,
            "to": to,
            "subject": subject,
        }
        if html_body:
            payload["html"] = html_body
        if plain_body:
            payload["text"] = plain_body
        if reply_to:
            payload["reply_to"] = reply_to
        if headers:
            payload["headers"] = headers
        if tags:
            payload["tags"] = tags
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self.BASE_URL}/emails",
                json=payload,
                headers=self._headers(),
            )
        if resp.status_code >= 400:
            raise ResendError(f"resend send failed [{resp.status_code}]: {resp.text}")
        data = resp.json()
        msg_id = str(data.get("id", ""))
        return ResendSendResult(message_id=msg_id, status="sent", raw=data)


__all__ = ["ResendClient", "ResendError", "ResendSendResult"]

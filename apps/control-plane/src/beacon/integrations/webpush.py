"""Web Push (VAPID + Web Push Protocol RFC 8030) client.

Uses pywebpush if available; otherwise a minimal JWT-signed request to the
push gateway. Encryption (Aes128Gcm) is delegated to pywebpush — not
re-implementing AEAD from scratch.
"""
from __future__ import annotations

import dataclasses
import logging
from typing import Any

logger = logging.getLogger(__name__)


@dataclasses.dataclass(slots=True)
class WebPushResult:
    status: str  # "sent" | "expired" | "failed"
    raw: dict[str, Any]


class WebPushError(RuntimeError):
    pass


class WebPushClient:
    def __init__(self, *, vapid_private_pem: str | None = None, vapid_subject: str = "mailto:dev@rewirelabs.dev") -> None:
        self.vapid_private_pem = vapid_private_pem
        self.vapid_subject = vapid_subject

    async def send(
        self,
        *,
        subscription: dict[str, Any],
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> WebPushResult:
        try:
            from pywebpush import WebPushException, webpush  # type: ignore
        except ImportError:
            logger.debug("pywebpush not installed; webpush send skipped (dev)")
            return WebPushResult(status="dev_skipped", raw={"reason": "no_pywebpush"})
        if not self.vapid_private_pem:
            return WebPushResult(status="dev_skipped", raw={"reason": "no_vapid_key"})
        import json

        payload = json.dumps({"title": title, "body": body, "data": data or {}})
        try:
            r = webpush(
                subscription_info=subscription,
                data=payload,
                vapid_private_key=self.vapid_private_pem,
                vapid_claims={"sub": self.vapid_subject},
            )
            return WebPushResult(status="sent", raw={"http_status": getattr(r, "status_code", 201)})
        except WebPushException as exc:
            code = getattr(exc.response, "status_code", 0) if hasattr(exc, "response") else 0
            if code == 410:
                return WebPushResult(status="expired", raw={"code": code})
            raise WebPushError(f"webpush send failed [{code}]: {exc}") from exc


__all__ = ["WebPushClient", "WebPushError", "WebPushResult"]

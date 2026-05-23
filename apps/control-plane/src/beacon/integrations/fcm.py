"""FCM (Firebase Cloud Messaging) HTTP v1 client.

Auth uses Service Account JSON (oauth2 access token) — refreshed every 50min.
"""
from __future__ import annotations

import dataclasses
import json
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclasses.dataclass(slots=True)
class FcmSendResult:
    status: str  # "sent" | "bad_token" | "failed"
    message_name: str
    raw: dict[str, Any]


class FcmError(RuntimeError):
    pass


class FcmClient:
    SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
    TOKEN_URL = "https://oauth2.googleapis.com/token"

    def __init__(self, *, service_account_json: str | None = None, timeout: float = 10.0) -> None:
        self._sa_json = service_account_json
        self._sa: dict[str, Any] | None = json.loads(service_account_json) if service_account_json else None
        self._timeout = timeout
        self._access_token: str | None = None
        self._expires_at: float = 0.0
        self.project_id = self._sa.get("project_id") if self._sa else None

    async def _access(self) -> str:
        now = time.time()
        if self._access_token and (self._expires_at - now) > 600:
            return self._access_token
        if not self._sa:
            raise FcmError("service_account_json not provided")
        try:
            from cryptography.hazmat.primitives import hashes  # type: ignore
            from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15  # type: ignore
            from cryptography.hazmat.primitives.serialization import load_pem_private_key  # type: ignore
        except ImportError:
            raise FcmError("cryptography lib required for FCM JWT")
        import base64

        header = {"alg": "RS256", "typ": "JWT"}
        iat = int(now)
        claim = {
            "iss": self._sa["client_email"],
            "scope": self.SCOPE,
            "aud": self.TOKEN_URL,
            "iat": iat,
            "exp": iat + 3600,
        }

        def _b64u(b: bytes) -> str:
            return base64.urlsafe_b64encode(b).decode().rstrip("=")

        h = _b64u(json.dumps(header, separators=(",", ":")).encode())
        p = _b64u(json.dumps(claim, separators=(",", ":")).encode())
        msg = f"{h}.{p}".encode()
        key = load_pem_private_key(self._sa["private_key"].encode(), password=None)
        sig = key.sign(msg, PKCS1v15(), hashes.SHA256())
        assertion = f"{h}.{p}.{_b64u(sig)}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                self.TOKEN_URL,
                data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion},
            )
        if resp.status_code != 200:
            raise FcmError(f"fcm token exchange failed: {resp.text}")
        body = resp.json()
        self._access_token = body["access_token"]
        self._expires_at = now + body.get("expires_in", 3600)
        return self._access_token

    async def send(
        self,
        *,
        device_token: str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> FcmSendResult:
        if not self.project_id:
            return FcmSendResult(status="dev_skipped", message_name="", raw={"reason": "no_sa"})
        try:
            access = await self._access()
        except FcmError as exc:
            logger.debug("fcm access error: %s", exc)
            return FcmSendResult(status="dev_skipped", message_name="", raw={"reason": str(exc)})
        url = f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"
        payload = {
            "message": {
                "token": device_token,
                "notification": {"title": title, "body": body},
            }
        }
        if data:
            payload["message"]["data"] = {k: str(v) for k, v in data.items()}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(url, json=payload, headers={"Authorization": f"Bearer {access}"})
        if resp.status_code == 200:
            return FcmSendResult(status="sent", message_name=resp.json().get("name", ""), raw=resp.json())
        if resp.status_code in (400, 404):
            return FcmSendResult(status="bad_token", message_name="", raw=resp.json() if resp.content else {})
        raise FcmError(f"fcm send failed [{resp.status_code}]: {resp.text}")


__all__ = ["FcmClient", "FcmError", "FcmSendResult"]

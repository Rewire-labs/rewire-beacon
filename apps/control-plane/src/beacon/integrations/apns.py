"""APNs (Apple Push Notification service) client.

Uses token-based auth (.p8 JWT) — preferred over cert pinning per Apple recommendation.
Each org uploads their .p8 + key_id + team_id; we generate JWT per request.
"""
from __future__ import annotations

import dataclasses
import json
import logging
import time
from typing import Any

import httpx

from beacon.settings import get_settings

logger = logging.getLogger(__name__)


@dataclasses.dataclass(slots=True)
class ApnsSendResult:
    status: str  # "sent" | "bad_token" | "failed"
    apns_id: str
    raw: dict[str, Any]


class ApnsError(RuntimeError):
    pass


class ApnsClient:
    PROD_HOST = "api.push.apple.com"
    SANDBOX_HOST = "api.sandbox.push.apple.com"

    def __init__(
        self,
        *,
        team_id: str | None = None,
        key_id: str | None = None,
        p8_pem: str | None = None,
        bundle_id: str = "",
        sandbox: bool = False,
        timeout: float = 10.0,
    ) -> None:
        s = get_settings()
        self.team_id = team_id or s.apns_team_id
        self.key_id = key_id or s.apns_key_id
        self.p8_pem = p8_pem
        self.bundle_id = bundle_id
        self.sandbox = sandbox
        self._timeout = timeout
        self._jwt: str | None = None
        self._jwt_expires_at: float = 0.0

    def _generate_jwt(self) -> str:
        # APNs JWT TTL is 1h max; refresh at 50min.
        now = time.time()
        if self._jwt and (self._jwt_expires_at - now) > 600:
            return self._jwt
        try:
            from cryptography.hazmat.primitives.serialization import load_pem_private_key  # type: ignore
            from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature  # type: ignore
            from cryptography.hazmat.primitives import hashes  # type: ignore
        except ImportError:
            raise ApnsError("cryptography lib required for APNs JWT")
        if not self.p8_pem:
            raise ApnsError("p8_pem not provided")
        import base64

        header = {"alg": "ES256", "kid": self.key_id}
        payload = {"iss": self.team_id, "iat": int(now)}

        def _b64u(b: bytes) -> str:
            return base64.urlsafe_b64encode(b).decode().rstrip("=")

        h = _b64u(json.dumps(header, separators=(",", ":")).encode())
        p = _b64u(json.dumps(payload, separators=(",", ":")).encode())
        message = f"{h}.{p}".encode()
        key = load_pem_private_key(self.p8_pem.encode(), password=None)
        raw = key.sign(message, signature_algorithm=__import__("cryptography.hazmat.primitives.asymmetric.ec", fromlist=["ECDSA"]).ECDSA(hashes.SHA256()))
        # Convert DER → raw 64 bytes (r||s).
        from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature  # type: ignore

        r, s = decode_dss_signature(raw)
        sig = r.to_bytes(32, "big") + s.to_bytes(32, "big")
        self._jwt = f"{h}.{p}.{_b64u(sig)}"
        self._jwt_expires_at = now + 3000
        return self._jwt

    async def send(
        self,
        *,
        device_token: str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
        priority: int = 10,
    ) -> ApnsSendResult:
        host = self.SANDBOX_HOST if self.sandbox else self.PROD_HOST
        url = f"https://{host}/3/device/{device_token}"
        try:
            jwt = self._generate_jwt()
        except ApnsError:
            # No crypto lib — return placeholder in dev.
            return ApnsSendResult(status="dev_skipped", apns_id="", raw={"reason": "no_crypto_lib"})
        payload = {
            "aps": {
                "alert": {"title": title, "body": body},
                "sound": "default",
            }
        }
        if data:
            payload.update(data)
        headers = {
            "authorization": f"bearer {jwt}",
            "apns-topic": self.bundle_id,
            "apns-push-type": "alert",
            "apns-priority": str(priority),
        }
        async with httpx.AsyncClient(timeout=self._timeout, http2=True) as client:
            resp = await client.post(url, json=payload, headers=headers)
        apns_id = resp.headers.get("apns-id", "")
        if resp.status_code == 200:
            return ApnsSendResult(status="sent", apns_id=apns_id, raw={})
        if resp.status_code in (400, 410):
            return ApnsSendResult(status="bad_token", apns_id=apns_id, raw=resp.json() if resp.content else {})
        raise ApnsError(f"apns send failed [{resp.status_code}]: {resp.text}")


__all__ = ["ApnsClient", "ApnsError", "ApnsSendResult"]

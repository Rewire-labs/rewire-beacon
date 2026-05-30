"""Push router — platform-based: iOS → APNs / Android → FCM / web → VAPID.

Unlike email/sms routers (where providers race for the same recipient),
push routing is deterministic per ``device.platform``. Each platform has a
single provider; the router exists to give callers a unified interface and
to keep per-provider failure/CB metrics decoupled.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Literal

from messaging_cp.adapters._circuit import ProviderCircuit  # RW-MESSAGING-23
from messaging_cp.adapters.push.apns import ApnsAdapter, ApnsAdapterError
from messaging_cp.adapters.push.fcm import FcmAdapter, FcmAdapterError

logger = logging.getLogger(__name__)

Platform = Literal["ios", "android", "web"]

_Circuit = ProviderCircuit  # backward compat alias


class PushRouterError(RuntimeError):
    pass


class PushRouterCircuitOpen(PushRouterError):
    """Raised when the provider for a given platform is circuit-open."""


@dataclass(slots=True)
class PushRouterResult:
    provider: str  # "apns" | "fcm" | "vapid"
    platform: str
    status: str
    message_id: str
    raw: dict[str, Any] = field(default_factory=dict)


class PushRouter:
    """Routes push deliveries by ``platform``.

    Web push (VAPID) is V0.3 — for V0 ``web`` platform raises
    ``NotImplementedError`` until VAPID adapter lands.
    """

    def __init__(
        self,
        *,
        apns: ApnsAdapter | None = None,
        fcm: FcmAdapter | None = None,
        cb_failure_threshold: int = 3,
        cb_reset_seconds: float = 30.0,
    ) -> None:
        self._apns = apns or ApnsAdapter()
        self._fcm = fcm or FcmAdapter()
        self._cb_apns = ProviderCircuit(
            failure_threshold=cb_failure_threshold,
            reset_after_seconds=cb_reset_seconds,
        )
        self._cb_fcm = ProviderCircuit(
            failure_threshold=cb_failure_threshold,
            reset_after_seconds=cb_reset_seconds,
        )

    async def send(
        self,
        *,
        platform: Platform,
        device_token: str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> PushRouterResult:
        if platform == "ios":
            if self._cb_apns.is_open():
                raise PushRouterCircuitOpen("apns circuit open")
            try:
                res = await self._apns.send(
                    device_token=device_token, title=title, body=body, data=data
                )
                self._cb_apns.record_success()
                return PushRouterResult(
                    provider="apns",
                    platform="ios",
                    status=res.status,
                    message_id=res.apns_id,
                    raw=res.raw,
                )
            except ApnsAdapterError as exc:
                self._cb_apns.record_failure()
                logger.warning("push_router.apns_failed", extra={"error": str(exc)})
                raise PushRouterError(f"apns failed: {exc}") from exc

        if platform == "android":
            if self._cb_fcm.is_open():
                raise PushRouterCircuitOpen("fcm circuit open")
            try:
                res = await self._fcm.send(
                    device_token=device_token, title=title, body=body, data=data
                )
                self._cb_fcm.record_success()
                return PushRouterResult(
                    provider="fcm",
                    platform="android",
                    status=res.status,
                    message_id=res.message_name,
                    raw=res.raw,
                )
            except FcmAdapterError as exc:
                self._cb_fcm.record_failure()
                logger.warning("push_router.fcm_failed", extra={"error": str(exc)})
                raise PushRouterError(f"fcm failed: {exc}") from exc

        if platform == "web":
            # V0.3 — VAPID adapter ships when push_web is GA. Use
            # beacon.integrations.webpush for the legacy path until then.
            raise NotImplementedError(
                "web push (VAPID) ships V0.3 — use beacon.integrations.webpush in legacy mode"
            )

        raise PushRouterError(f"unknown platform: {platform}")


__all__ = ["PushRouter", "PushRouterResult", "PushRouterError", "PushRouterCircuitOpen"]

"""Push adapters — APNs (iOS) + FCM (Android) + router (platform routing)."""

from __future__ import annotations

from messaging_cp.adapters.push.apns import ApnsAdapter, ApnsAdapterError
from messaging_cp.adapters.push.fcm import FcmAdapter, FcmAdapterError
from messaging_cp.adapters.push.router import PushRouter, PushRouterResult

__all__ = [
    "ApnsAdapter",
    "ApnsAdapterError",
    "FcmAdapter",
    "FcmAdapterError",
    "PushRouter",
    "PushRouterResult",
]

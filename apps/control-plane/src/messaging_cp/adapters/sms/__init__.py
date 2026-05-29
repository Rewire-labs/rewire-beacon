"""SMS adapters — Zenvia primary (BR), TotalVoice fallback."""

from __future__ import annotations

from messaging_cp.adapters.sms.zenvia import ZenviaAdapter, ZenviaAdapterError
from messaging_cp.adapters.sms.router import SmsRouter, SmsRouterResult

__all__ = [
    "ZenviaAdapter",
    "ZenviaAdapterError",
    "SmsRouter",
    "SmsRouterResult",
]

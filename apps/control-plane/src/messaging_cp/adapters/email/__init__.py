"""Email adapters — Postal primary + Resend fallback."""

from __future__ import annotations

from messaging_cp.adapters.email.postal import PostalAdapter, PostalAdapterError
from messaging_cp.adapters.email.resend import ResendAdapter, ResendAdapterError
from messaging_cp.adapters.email.router import EmailRouter, EmailRouterResult

__all__ = [
    "PostalAdapter",
    "PostalAdapterError",
    "ResendAdapter",
    "ResendAdapterError",
    "EmailRouter",
    "EmailRouterResult",
]

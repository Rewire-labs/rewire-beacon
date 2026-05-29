"""Canonical adapter namespace for rewire-messaging V0.

Multi-provider, multi-channel routing layer:

- ``email/`` — Postal (primary, self-hosted) → Resend (fallback)
- ``sms/``   — Zenvia (primary BR) → TotalVoice (fallback)
- ``push/``  — APNs (iOS) / FCM (Android) / VAPID (web)

Each channel exposes:
- ``<provider>.py`` thin client wrappers
- ``router.py`` with circuit breaker + provider election + fallback

All routers use ``rewire_shared.http_client.ResilientHTTPClient`` for
retry+timeout+CB and emit ``rewire_shared.metrics`` per-provider counters.
"""

from __future__ import annotations

__all__: list[str] = []

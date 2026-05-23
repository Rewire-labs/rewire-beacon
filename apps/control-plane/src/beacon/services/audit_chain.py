"""BLAKE3 audit chain hashing + CITADEL anchor (async fire-and-forget).

Hash inputs (deterministic):
  organization_id | recipient | channel | content_digest | timestamp | consent_basis
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

import httpx

from beacon.settings import get_settings


def _hasher(data: bytes) -> str:
    try:
        import blake3  # type: ignore

        return blake3.blake3(data).hexdigest()
    except ImportError:
        # Fallback to sha3-256 if blake3 unavailable; collision-resistant enough for V0.
        return hashlib.sha3_256(data).hexdigest()


def compute_chain_hash(
    *,
    organization_id: str,
    recipient: str,
    channel: str,
    content: str,
    timestamp: datetime,
    consent_basis: str | None,
) -> str:
    content_digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    parts = [
        organization_id,
        recipient,
        channel,
        content_digest,
        timestamp.isoformat(),
        consent_basis or "",
    ]
    serialized = "\n".join(parts).encode("utf-8")
    return _hasher(serialized)


async def anchor_to_citadel(*, hash_hex: str, metadata: dict[str, Any]) -> None:
    """Fire-and-forget POST to CITADEL chain. Failures logged, never raised."""
    import logging

    log = logging.getLogger(__name__)
    s = get_settings()
    url = f"{s.citadel_chain_base_url.rstrip('/')}/chain/append"
    payload = {"hash": hash_hex, "system": "beacon", "metadata": metadata}
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code >= 400:
                log.warning("citadel.anchor_failed status=%s body=%s", resp.status_code, resp.text)
    except Exception as exc:  # noqa: BLE001
        log.warning("citadel.anchor_unreachable: %s", exc)

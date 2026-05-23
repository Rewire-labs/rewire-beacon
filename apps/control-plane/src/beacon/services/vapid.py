"""VAPID key management per org.

Each org has 1 active VAPID keypair (P-256). Public key shared with client
for subscription; private key stored at vault path (env in dev).

Persistence: senders.push_apps with platform='web' + vapid_public_key +
vapid_private_key_vault_path. We don't store the private key in Postgres.
"""
from __future__ import annotations

import base64
import logging
import secrets
from typing import Any

logger = logging.getLogger(__name__)


def generate_vapid_keypair() -> tuple[str, str]:
    """Returns (public_b64url_uncompressed, private_pem)."""
    try:
        from cryptography.hazmat.primitives import serialization  # type: ignore
        from cryptography.hazmat.primitives.asymmetric import ec  # type: ignore

        key = ec.generate_private_key(ec.SECP256R1())
        private_pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()
        pub_numbers = key.public_key().public_numbers()
        # Uncompressed point: 0x04 | X (32B) | Y (32B), then base64url no pad.
        uncompressed = b"\x04" + pub_numbers.x.to_bytes(32, "big") + pub_numbers.y.to_bytes(32, "big")
        public_b64 = base64.urlsafe_b64encode(uncompressed).decode().rstrip("=")
        return public_b64, private_pem
    except ImportError:
        marker = secrets.token_urlsafe(32)
        return f"DEV-PUB-{marker}", f"DEV-PRIV-{marker}"

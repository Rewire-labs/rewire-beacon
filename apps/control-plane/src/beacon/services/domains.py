"""Email domain provisioning + DKIM/SPF/DMARC verification.

Verification flow:
1. Org calls `POST /v1/domains` with domain name.
2. We generate a 2048-bit DKIM keypair, store public key for DNS instruction,
   private key path stays in Vault (placeholder path in dev).
3. Provision a Postal "server" (vhost) for the org-domain combo.
4. Org adds DNS records: DKIM TXT, SPF TXT, DMARC TXT, optional return-path CNAME.
5. Org calls `POST /v1/domains/{id}/verify` to trigger DNS lookup.
6. We resolve the records and update `email_domains.verified=true` + status cols.

DNS lookup uses dnspython (optional dep). In dev/no-dns, we mark verified=true
to unblock local testing when `BEACON_ENV=dev`.
"""
from __future__ import annotations

import base64
import logging
import os
import secrets
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beacon.db.models import EmailDomain
from beacon.integrations.postal import PostalClient, PostalError
from beacon.settings import get_settings

logger = logging.getLogger(__name__)


def _generate_dkim_keypair() -> tuple[str, str]:
    """Return (public_pem, private_pem). Falls back to placeholder if no crypto lib."""
    try:
        from cryptography.hazmat.primitives import serialization  # type: ignore
        from cryptography.hazmat.primitives.asymmetric import rsa  # type: ignore

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        priv = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()
        pub = (
            key.public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode()
        )
        return pub, priv
    except ImportError:
        # Placeholder — dev only.
        marker = secrets.token_urlsafe(32)
        return f"DEV-PLACEHOLDER-PUBKEY-{marker}", f"DEV-PLACEHOLDER-PRIVKEY-{marker}"


def _dkim_public_to_txt_value(public_pem: str) -> str:
    """Convert PEM SubjectPublicKeyInfo to DKIM TXT record `v=DKIM1; k=rsa; p=<base64>`."""
    body = public_pem.replace("-----BEGIN PUBLIC KEY-----", "").replace(
        "-----END PUBLIC KEY-----", ""
    ).replace("\n", "").strip()
    if not body:
        body = base64.b64encode(b"placeholder").decode()
    return f"v=DKIM1; k=rsa; p={body}"


async def create_domain(
    session: AsyncSession,
    *,
    organization_id: str,
    domain: str,
) -> EmailDomain:
    domain = domain.lower().strip()
    pub_pem, _priv_pem = _generate_dkim_keypair()
    row = EmailDomain(
        organization_id=organization_id,
        domain=domain,
        verified=False,
        dkim_public_key=pub_pem,
        dkim_selector="beacon",
        spf_status="pending",
        dmarc_status="pending",
    )
    session.add(row)
    await session.flush()
    # Best-effort Postal vhost provisioning.
    try:
        client = PostalClient()
        s = get_settings()
        await client.create_server_for_domain(
            organization_slug=organization_id[:8], name=f"{domain}-{s.environment}"
        )
        row.postal_vhost_id = f"vhost-{row.id}"
    except (PostalError, Exception) as exc:  # noqa: BLE001
        logger.warning("postal_vhost_create_skipped: %s", exc)
    await session.commit()
    return row


async def list_domains(session: AsyncSession, organization_id: str) -> list[EmailDomain]:
    stmt = (
        select(EmailDomain)
        .where(EmailDomain.organization_id == organization_id)
        .order_by(EmailDomain.created_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def verify_domain(session: AsyncSession, organization_id: str, domain_id: str) -> EmailDomain:
    row = await session.get(EmailDomain, domain_id)
    if row is None or row.organization_id != organization_id:
        raise LookupError(f"domain not found: {domain_id}")

    # Resolve DNS records.
    dkim_ok = await _check_dkim(row.domain, row.dkim_selector, row.dkim_public_key or "")
    spf_ok = await _check_spf(row.domain)
    dmarc_ok = await _check_dmarc(row.domain)

    row.spf_status = "pass" if spf_ok else "fail"
    row.dmarc_status = "pass" if dmarc_ok else "fail"
    s = get_settings()
    if dkim_ok and spf_ok and dmarc_ok:
        row.verified = True
        row.verified_at = datetime.now(UTC)
    elif s.environment == "dev" and os.environ.get("BEACON_FORCE_VERIFY", "0") == "1":
        row.verified = True
        row.verified_at = datetime.now(UTC)
    await session.commit()
    return row


def domain_dns_instructions(row: EmailDomain) -> dict[str, Any]:
    return {
        "domain": row.domain,
        "records": [
            {
                "type": "TXT",
                "name": f"{row.dkim_selector}._domainkey.{row.domain}",
                "value": _dkim_public_to_txt_value(row.dkim_public_key or ""),
                "purpose": "DKIM",
            },
            {
                "type": "TXT",
                "name": row.domain,
                "value": "v=spf1 include:mail.beacon.rewirelabs.dev ~all",
                "purpose": "SPF",
            },
            {
                "type": "TXT",
                "name": f"_dmarc.{row.domain}",
                "value": "v=DMARC1; p=quarantine; rua=mailto:dmarc-reports@beacon.rewirelabs.dev",
                "purpose": "DMARC",
            },
        ],
    }


# ----- DNS lookup helpers (dnspython optional) ----------------------------


async def _check_dkim(domain: str, selector: str, expected_public_pem: str) -> bool:
    txt_name = f"{selector}._domainkey.{domain}"
    records = await _resolve_txt(txt_name)
    if not records:
        return False
    expected_value = _dkim_public_to_txt_value(expected_public_pem)
    return any(expected_value.split("p=")[-1][:40] in r for r in records)


async def _check_spf(domain: str) -> bool:
    records = await _resolve_txt(domain)
    return any("v=spf1" in r and "beacon.rewirelabs.dev" in r for r in records)


async def _check_dmarc(domain: str) -> bool:
    records = await _resolve_txt(f"_dmarc.{domain}")
    return any("v=DMARC1" in r for r in records)


async def _resolve_txt(name: str) -> list[str]:
    try:
        import dns.asyncresolver  # type: ignore

        try:
            answer = await dns.asyncresolver.resolve(name, "TXT")
            return ["".join(r.strings_unicode if hasattr(r, "strings_unicode") else [s.decode() for s in r.strings]) for r in answer]
        except Exception as exc:  # noqa: BLE001 — NXDOMAIN, NoAnswer, etc
            logger.debug("dns lookup miss %s: %s", name, exc)
            return []
    except ImportError:
        logger.debug("dnspython not installed; skipping verify")
        return []

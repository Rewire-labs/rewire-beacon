"""Messaging hot-path service — enqueue messages for delivery.

Pipeline:
1. Validate sender domain belongs to org + verified.
2. Check suppression list (cross-canal lookup <2ms).
3. Check monthly quota (Postgres counter — Redis sliding optional).
4. Compute BLAKE3 chain hash.
5. Insert notification + pending delivery rows.
6. Publish to Kafka topic `beacon.send.<channel>.<tier>` (best-effort; if
   Kafka unavailable the row stays in `pending` state and a sweeper retries).
7. Fire-and-forget CITADEL anchor.

ULID for message_id (sortable + Kafka-partition-friendly).
"""
from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
import secrets
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from beacon.db.models import (
    Delivery,
    EmailDomain,
    Notification,
    Organization,
    SuppressionEntry,
)
from beacon.services.audit_chain import anchor_to_citadel, compute_chain_hash
from beacon.settings import get_settings

logger = logging.getLogger(__name__)


# ULID — simple impl (time-based 48-bit + 80 random bits, Crockford base32).
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def new_ulid() -> str:
    ts_ms = int(time.time() * 1000)
    rand = secrets.randbits(80)
    n = (ts_ms << 80) | rand
    out = []
    for _ in range(26):
        out.append(_CROCKFORD[n & 0x1F])
        n >>= 5
    return "".join(reversed(out))


@dataclasses.dataclass(slots=True)
class EmailMessageRequest:
    sender: str
    to: list[str]
    subject: str
    html_body: str | None = None
    plain_body: str | None = None
    template_slug: str | None = None
    consent_basis: str | None = None
    metadata: dict[str, Any] | None = None


@dataclasses.dataclass(slots=True)
class EnqueuedMessage:
    message_id: str
    status: str  # "queued"
    chain_hash: str
    provider_route: str  # "postal" | "ses"


class SuppressedError(Exception):
    """Raised when recipient is on the suppression list."""


class QuotaExceededError(Exception):
    pass


class InvalidSenderError(Exception):
    pass


async def _validate_sender(session: AsyncSession, org_id: str, sender_addr: str) -> EmailDomain:
    """Sender must be `local@domain` whose domain is verified for the org."""
    if "@" not in sender_addr:
        raise InvalidSenderError(f"invalid sender address: {sender_addr}")
    domain = sender_addr.split("@", 1)[1].lower()
    stmt = select(EmailDomain).where(
        EmailDomain.organization_id == org_id, EmailDomain.domain == domain
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise InvalidSenderError(f"domain not owned by org: {domain}")
    if not row.verified:
        raise InvalidSenderError(f"domain not verified: {domain}")
    return row


async def _check_suppression(session: AsyncSession, org_id: str, recipient: str) -> None:
    stmt = select(SuppressionEntry.id).where(
        SuppressionEntry.organization_id == org_id,
        SuppressionEntry.identifier_type == "email",
        SuppressionEntry.identifier_value == recipient.lower(),
    )
    if (await session.execute(stmt)).first():
        raise SuppressedError(f"recipient suppressed: {recipient}")


async def _check_quota(session: AsyncSession, org_id: str, channel: str = "email") -> str:
    org = await session.get(Organization, org_id)
    if org is None:
        raise InvalidSenderError(f"organization not found: {org_id}")
    if channel == "email" and org.monthly_quota_email <= 0:
        raise QuotaExceededError("monthly email quota exhausted")
    return org.tier


async def _publish_kafka(topic: str, key: str, value: dict[str, Any]) -> None:
    """Best-effort Kafka publish. Silently degrades in dev."""
    try:
        from aiokafka import AIOKafkaProducer  # type: ignore
    except ImportError:
        logger.debug("aiokafka not installed; skipping publish to %s", topic)
        return
    s = get_settings()
    producer = AIOKafkaProducer(
        bootstrap_servers=s.kafka_brokers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8"),
        acks="all",
        enable_idempotence=True,
    )
    await producer.start()
    try:
        await producer.send_and_wait(topic, value=value, key=key)
    finally:
        await producer.stop()


async def enqueue_email(
    session: AsyncSession,
    *,
    organization_id: str,
    req: EmailMessageRequest,
) -> EnqueuedMessage:
    # 1. Validate sender
    await _validate_sender(session, organization_id, req.sender)
    # 2. Suppression — fail on first suppressed recipient (per-recipient API caller).
    for recipient in req.to:
        await _check_suppression(session, organization_id, recipient)
    # 3. Quota
    tier = await _check_quota(session, organization_id, "email")

    # 4. Chain hash
    now = datetime.now(UTC)
    content = (req.html_body or "") + "\n" + (req.plain_body or "")
    primary_recipient = req.to[0]
    chain_hash = compute_chain_hash(
        organization_id=organization_id,
        recipient=primary_recipient,
        channel="email",
        content=content,
        timestamp=now,
        consent_basis=req.consent_basis,
    )

    # 5. Insert notification + pending delivery
    message_id = new_ulid()
    notif = Notification(
        id=message_id,
        tenant_id=organization_id,  # legacy schema uses tenant_id
        channel_kind="email",
        recipient=primary_recipient,
        payload={
            "sender": req.sender,
            "to": req.to,
            "subject": req.subject,
            "template_slug": req.template_slug,
            "metadata": req.metadata or {},
        },
        consent_basis=req.consent_basis,
        audit_chain_hash=chain_hash,
        created_at=now,
    )
    delivery = Delivery(
        notification_id=message_id,
        provider="postal",
        status="pending",
        attempts=0,
        created_at=now,
    )
    session.add(notif)
    session.add(delivery)
    await session.flush()
    await session.commit()

    # 6. Kafka publish (don't block on Kafka failure — sweeper picks up `pending`)
    envelope = {
        "message_id": message_id,
        "organization_id": organization_id,
        "sender": req.sender,
        "to": req.to,
        "subject": req.subject,
        "html_body": req.html_body,
        "plain_body": req.plain_body,
        "template_slug": req.template_slug,
        "consent_basis": req.consent_basis,
        "chain_hash": chain_hash,
        "enqueued_at": now.isoformat(),
    }
    topic = f"beacon.send.email.{tier}"
    asyncio.create_task(_safe_publish(topic, message_id, envelope))

    # 7. CITADEL anchor (async)
    asyncio.create_task(
        anchor_to_citadel(
            hash_hex=chain_hash,
            metadata={
                "message_id": message_id,
                "organization_id": organization_id,
                "channel": "email",
                "recipient": primary_recipient,
                "consent_basis": req.consent_basis,
                "timestamp": now.isoformat(),
            },
        )
    )

    return EnqueuedMessage(
        message_id=message_id, status="queued", chain_hash=chain_hash, provider_route="postal"
    )


async def _safe_publish(topic: str, key: str, value: dict[str, Any]) -> None:
    try:
        await _publish_kafka(topic, key, value)
    except Exception as exc:  # noqa: BLE001
        logger.warning("kafka_publish_failed topic=%s key=%s err=%s", topic, key, exc)

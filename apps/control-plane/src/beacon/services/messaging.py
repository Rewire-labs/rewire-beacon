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


# ============================================================ SMS hot path


@dataclasses.dataclass(slots=True)
class SmsMessageRequest:
    to: str  # E.164 e.g. +5511999990001
    text: str
    from_number: str | None = None
    template_slug: str | None = None
    consent_basis: str | None = None
    metadata: dict[str, Any] | None = None


async def enqueue_sms(
    session: AsyncSession,
    *,
    organization_id: str,
    req: SmsMessageRequest,
) -> EnqueuedMessage:
    # Suppression.
    stmt = select(SuppressionEntry.id).where(
        SuppressionEntry.organization_id == organization_id,
        SuppressionEntry.identifier_type == "phone_e164",
        SuppressionEntry.identifier_value == req.to,
    )
    if (await session.execute(stmt)).first():
        raise SuppressedError(f"recipient suppressed: {req.to}")

    org = await session.get(Organization, organization_id)
    if org is None:
        raise InvalidSenderError(f"organization not found: {organization_id}")
    if org.monthly_quota_sms <= 0:
        raise QuotaExceededError("monthly sms quota exhausted")
    tier = org.tier

    now = datetime.now(UTC)
    chain_hash = compute_chain_hash(
        organization_id=organization_id,
        recipient=req.to,
        channel="sms",
        content=req.text,
        timestamp=now,
        consent_basis=req.consent_basis,
    )

    message_id = new_ulid()
    notif = Notification(
        id=message_id,
        tenant_id=organization_id,
        channel_kind="sms",
        recipient=req.to,
        payload={"text": req.text, "from_number": req.from_number, "metadata": req.metadata or {}},
        consent_basis=req.consent_basis,
        audit_chain_hash=chain_hash,
        created_at=now,
    )
    delivery = Delivery(
        notification_id=message_id, provider="zenvia", status="pending",
        attempts=0, created_at=now,
    )
    session.add(notif)
    session.add(delivery)
    await session.flush()
    await session.commit()

    envelope = {
        "message_id": message_id,
        "organization_id": organization_id,
        "to": req.to,
        "text": req.text,
        "from_number": req.from_number,
        "chain_hash": chain_hash,
        "enqueued_at": now.isoformat(),
    }
    asyncio.create_task(_safe_publish(f"beacon.send.sms.{tier}", message_id, envelope))
    asyncio.create_task(
        anchor_to_citadel(
            hash_hex=chain_hash,
            metadata={
                "message_id": message_id, "organization_id": organization_id,
                "channel": "sms", "recipient": req.to, "timestamp": now.isoformat(),
            },
        )
    )
    return EnqueuedMessage(
        message_id=message_id, status="queued", chain_hash=chain_hash, provider_route="zenvia"
    )


# ============================================================ Push hot path


@dataclasses.dataclass(slots=True)
class PushMessageRequest:
    device_token: str
    title: str
    body: str
    platform: str  # ios|android|web
    data: dict[str, Any] | None = None
    consent_basis: str | None = None
    push_app_id: str | None = None


async def enqueue_push(
    session: AsyncSession,
    *,
    organization_id: str,
    req: PushMessageRequest,
) -> EnqueuedMessage:
    stmt = select(SuppressionEntry.id).where(
        SuppressionEntry.organization_id == organization_id,
        SuppressionEntry.identifier_type == "push_token",
        SuppressionEntry.identifier_value == req.device_token,
    )
    if (await session.execute(stmt)).first():
        raise SuppressedError(f"recipient suppressed: {req.device_token[:8]}...")

    org = await session.get(Organization, organization_id)
    if org is None:
        raise InvalidSenderError(f"organization not found: {organization_id}")
    if org.monthly_quota_push <= 0:
        raise QuotaExceededError("monthly push quota exhausted")
    tier = org.tier

    now = datetime.now(UTC)
    content = f"{req.title}\n{req.body}"
    chain_hash = compute_chain_hash(
        organization_id=organization_id,
        recipient=req.device_token,
        channel=f"push_{req.platform}",
        content=content,
        timestamp=now,
        consent_basis=req.consent_basis,
    )
    message_id = new_ulid()
    notif = Notification(
        id=message_id,
        tenant_id=organization_id,
        channel_kind=f"push_{req.platform}",
        recipient=req.device_token,
        payload={
            "title": req.title, "body": req.body, "data": req.data or {},
            "push_app_id": req.push_app_id, "platform": req.platform,
        },
        consent_basis=req.consent_basis,
        audit_chain_hash=chain_hash,
        created_at=now,
    )
    provider_default = {"ios": "apns", "android": "fcm", "web": "webpush"}[req.platform]
    delivery = Delivery(
        notification_id=message_id, provider=provider_default, status="pending",
        attempts=0, created_at=now,
    )
    session.add(notif)
    session.add(delivery)
    await session.flush()
    await session.commit()

    envelope = {
        "message_id": message_id, "organization_id": organization_id,
        "device_token": req.device_token, "title": req.title, "body": req.body,
        "data": req.data or {}, "push_app_id": req.push_app_id,
        "platform": req.platform, "chain_hash": chain_hash,
    }
    topic = f"beacon.send.push.{req.platform}.{tier}"
    asyncio.create_task(_safe_publish(topic, message_id, envelope))
    asyncio.create_task(
        anchor_to_citadel(
            hash_hex=chain_hash,
            metadata={
                "message_id": message_id, "organization_id": organization_id,
                "channel": f"push_{req.platform}", "timestamp": now.isoformat(),
            },
        )
    )
    return EnqueuedMessage(
        message_id=message_id, status="queued", chain_hash=chain_hash, provider_route=provider_default
    )


# ============================================================ WhatsApp hot path (via CONNECT)


@dataclasses.dataclass(slots=True)
class WhatsAppMessageRequest:
    to: str  # E.164
    template_name: str
    template_vars: dict[str, Any] | None = None
    body_text: str | None = None  # for session messages within 24h window
    consent_basis: str | None = None


async def enqueue_whatsapp(
    session: AsyncSession,
    *,
    organization_id: str,
    req: WhatsAppMessageRequest,
) -> EnqueuedMessage:
    stmt = select(SuppressionEntry.id).where(
        SuppressionEntry.organization_id == organization_id,
        SuppressionEntry.identifier_type == "phone_e164",
        SuppressionEntry.identifier_value == req.to,
    )
    if (await session.execute(stmt)).first():
        raise SuppressedError(f"recipient suppressed: {req.to}")

    org = await session.get(Organization, organization_id)
    if org is None:
        raise InvalidSenderError(f"organization not found: {organization_id}")
    if org.monthly_quota_whatsapp <= 0:
        raise QuotaExceededError("monthly whatsapp quota exhausted")
    tier = org.tier

    now = datetime.now(UTC)
    content = req.body_text or f"template:{req.template_name}"
    chain_hash = compute_chain_hash(
        organization_id=organization_id,
        recipient=req.to,
        channel="whatsapp",
        content=content,
        timestamp=now,
        consent_basis=req.consent_basis,
    )
    message_id = new_ulid()
    notif = Notification(
        id=message_id, tenant_id=organization_id, channel_kind="whatsapp",
        recipient=req.to,
        payload={
            "template_name": req.template_name,
            "template_vars": req.template_vars or {},
            "body_text": req.body_text,
        },
        consent_basis=req.consent_basis,
        audit_chain_hash=chain_hash, created_at=now,
    )
    delivery = Delivery(
        notification_id=message_id, provider="connect", status="pending",
        attempts=0, created_at=now,
    )
    session.add(notif)
    session.add(delivery)
    await session.flush()
    await session.commit()

    envelope = {
        "message_id": message_id, "organization_id": organization_id,
        "to": req.to, "template_name": req.template_name,
        "template_vars": req.template_vars or {}, "body_text": req.body_text,
        "chain_hash": chain_hash,
    }
    asyncio.create_task(_safe_publish(f"beacon.send.whatsapp.{tier}", message_id, envelope))
    asyncio.create_task(
        anchor_to_citadel(
            hash_hex=chain_hash,
            metadata={
                "message_id": message_id, "organization_id": organization_id,
                "channel": "whatsapp", "recipient": req.to, "timestamp": now.isoformat(),
            },
        )
    )
    return EnqueuedMessage(
        message_id=message_id, status="queued", chain_hash=chain_hash, provider_route="connect"
    )

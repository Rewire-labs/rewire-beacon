"""BEACON SQLAlchemy 2 models — core entities (V0 skeleton).

Schema overview (from futuros_produtos.md secao 2.7):
- Tenant      — multi-tenant root (each customer org)
- Channel     — per-tenant channel config (email/sms/wa/push)
- Template    — render-ready transactional templates (MJML for email)
- Notification — single message dispatched (1:N deliveries possible across channels)
- Delivery    — actual provider attempt (one per channel/recipient)

V0 ships the table definitions only — no service layer wiring.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Canonical declarative base for BEACON models."""


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    channels: Mapped[list[Channel]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    templates: Mapped[list[Template]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )


class Channel(Base):
    __tablename__ = "channels"
    __table_args__ = (Index("ix_channels_tenant_kind", "tenant_id", "kind"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="email|sms|whatsapp|push_mobile|push_web"
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    tenant: Mapped[Tenant] = relationship(back_populates="channels")


class Template(Base):
    __tablename__ = "templates"
    __table_args__ = (Index("ix_templates_tenant_slug", "tenant_id", "slug"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    channel_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(512), nullable=True)
    body_source: Mapped[str] = mapped_column(
        Text, nullable=False, comment="MJML for email; raw text/JSON for others"
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    tenant: Mapped[Tenant] = relationship(back_populates="templates")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_tenant_created", "tenant_id", "created_at"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    template_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("templates.id", ondelete="SET NULL"), nullable=True
    )
    channel_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    recipient: Mapped[str] = mapped_column(String(512), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    consent_basis: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="LGPD lawful_basis tag"
    )
    audit_chain_hash: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="BLAKE3 hash anchored in CITADEL"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    tenant: Mapped[Tenant] = relationship(back_populates="notifications")
    deliveries: Mapped[list[Delivery]] = relationship(
        back_populates="notification", cascade="all, delete-orphan"
    )


class Delivery(Base):
    __tablename__ = "deliveries"
    __table_args__ = (Index("ix_deliveries_notification", "notification_id"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    notification_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="pending|sent|delivered|opened|clicked|failed|bounced|complained",
    )
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    notification: Mapped[Notification] = relationship(back_populates="deliveries")


__all__ = ["Base", "Channel", "Delivery", "Notification", "Template", "Tenant"]

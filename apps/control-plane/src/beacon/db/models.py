"""BEACON SQLAlchemy 2 models — production schema (V0.1+).

Schemas:
- beacon.*       : legacy core (tenants/channels/templates/notifications/deliveries) + api_tokens
- tenancy.*      : organizations + users + memberships
- senders.*      : email_domains + dedicated_ips + whatsapp_numbers + push_apps
- templates.*    : email_templates + sms_templates + push_templates
- suppression.*  : entries (cross-canal)
- webhooks.*     : endpoints + deliveries
- providers.*    : sms_provider_routes
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    """Canonical declarative base for BEACON models."""


# ============================================================ legacy core (beacon schema)


class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = ({"schema": "beacon"},)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    channels: Mapped[list[Channel]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    templates_legacy: Mapped[list[Template]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    notifications: Mapped[list[Notification]] = relationship(back_populates="tenant", cascade="all, delete-orphan")


class Channel(Base):
    __tablename__ = "channels"
    __table_args__ = (
        Index("ix_channels_tenant_kind", "tenant_id", "kind"),
        {"schema": "beacon"},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("beacon.tenants.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    tenant: Mapped[Tenant] = relationship(back_populates="channels")


class Template(Base):
    __tablename__ = "templates"
    __table_args__ = (
        Index("ix_templates_tenant_slug", "tenant_id", "slug"),
        {"schema": "beacon"},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("beacon.tenants.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    channel_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(512), nullable=True)
    body_source: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    tenant: Mapped[Tenant] = relationship(back_populates="templates_legacy")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_tenant_created", "tenant_id", "created_at"),
        {"schema": "beacon"},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("beacon.tenants.id", ondelete="CASCADE"), nullable=False
    )
    template_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("beacon.templates.id", ondelete="SET NULL"), nullable=True
    )
    channel_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    recipient: Mapped[str] = mapped_column(String(512), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    consent_basis: Mapped[str | None] = mapped_column(String(64), nullable=True)
    audit_chain_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    tenant: Mapped[Tenant] = relationship(back_populates="notifications")
    deliveries: Mapped[list[Delivery]] = relationship(back_populates="notification", cascade="all, delete-orphan")


class Delivery(Base):
    __tablename__ = "deliveries"
    __table_args__ = (
        Index("ix_deliveries_notification", "notification_id"),
        {"schema": "beacon"},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    notification_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("beacon.notifications.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    notification: Mapped[Notification] = relationship(back_populates="deliveries")


# ============================================================ tenancy schema


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = ({"schema": "tenancy"},)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tier: Mapped[str] = mapped_column(String(32), default="hobby", nullable=False)
    monthly_quota_email: Mapped[int] = mapped_column(Integer, default=5000, nullable=False)
    monthly_quota_sms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    monthly_quota_push: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    monthly_quota_whatsapp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class User(Base):
    __tablename__ = "users"
    __table_args__ = ({"schema": "tenancy"},)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_membership_org_user"),
        {"schema": "tenancy"},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenancy.organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenancy.users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(32), default="member", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


# ============================================================ senders schema


class EmailDomain(Base):
    __tablename__ = "email_domains"
    __table_args__ = (
        UniqueConstraint("organization_id", "domain", name="uq_email_domain_org"),
        Index("ix_email_domains_org", "organization_id"),
        {"schema": "senders"},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenancy.organizations.id", ondelete="CASCADE"), nullable=False
    )
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dkim_public_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    dkim_selector: Mapped[str] = mapped_column(String(64), default="beacon", nullable=False)
    spf_status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    dmarc_status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    reputation_score: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    postal_vhost_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DedicatedIp(Base):
    __tablename__ = "dedicated_ips"
    __table_args__ = ({"schema": "senders"},)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    organization_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tenancy.organizations.id", ondelete="SET NULL"), nullable=True
    )
    ip_address: Mapped[str] = mapped_column(String(45), unique=True, nullable=False)
    ptr_record: Mapped[str | None] = mapped_column(String(255), nullable=True)
    warmup_status: Mapped[str] = mapped_column(String(32), default="cold", nullable=False)
    warmup_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    warmup_target_daily: Mapped[int] = mapped_column(Integer, default=50000, nullable=False)
    current_daily_cap: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    reputation_score: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    postal_node: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class WhatsappNumber(Base):
    __tablename__ = "whatsapp_numbers"
    __table_args__ = (
        UniqueConstraint("organization_id", "phone_e164", name="uq_whatsapp_org_phone"),
        {"schema": "senders"},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenancy.organizations.id", ondelete="CASCADE"), nullable=False
    )
    phone_e164: Mapped[str] = mapped_column(String(20), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    connect_number_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    quality_rating: Mapped[str] = mapped_column(String(16), default="unknown", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class PushApp(Base):
    __tablename__ = "push_apps"
    __table_args__ = ({"schema": "senders"},)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenancy.organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    platform: Mapped[str] = mapped_column(String(16), nullable=False)
    bundle_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    apns_cert_vault_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    apns_key_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    apns_team_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fcm_service_account_vault_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    vapid_public_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    vapid_private_key_vault_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


# ============================================================ templates schema (richer)


class EmailTemplate(Base):
    __tablename__ = "email_templates"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", "version", name="uq_email_tpl_org_slug_ver"),
        {"schema": "templates"},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenancy.organizations.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    mjml_source: Mapped[str] = mapped_column(Text, nullable=False)
    text_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    variables_schema: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class SmsTemplate(Base):
    __tablename__ = "sms_templates"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", "version", name="uq_sms_tpl_org_slug_ver"),
        {"schema": "templates"},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenancy.organizations.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    variables_schema: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class PushTemplate(Base):
    __tablename__ = "push_templates"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", "version", name="uq_push_tpl_org_slug_ver"),
        {"schema": "templates"},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenancy.organizations.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    click_action: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    data_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    variables_schema: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


# ============================================================ suppression schema


class SuppressionEntry(Base):
    __tablename__ = "entries"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "identifier_type",
            "identifier_value",
            name="uq_suppression_lookup",
        ),
        {"schema": "suppression"},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenancy.organizations.id", ondelete="CASCADE"), nullable=False
    )
    identifier_type: Mapped[str] = mapped_column(String(16), nullable=False)
    identifier_value: Mapped[str] = mapped_column(String(512), nullable=False)
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    source_channel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ============================================================ webhooks schema


class WebhookEndpoint(Base):
    __tablename__ = "endpoints"
    __table_args__ = (
        Index("ix_webhooks_endpoints_org", "organization_id"),
        {"schema": "webhooks"},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenancy.organizations.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    event_types: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    signing_secret_vault_path: Mapped[str] = mapped_column(String(512), nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class WebhookDelivery(Base):
    __tablename__ = "deliveries"
    __table_args__ = (
        Index("ix_webhooks_deliveries_pending", "status", "next_attempt_at"),
        {"schema": "webhooks"},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    endpoint_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("webhooks.endpoints.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


# ============================================================ providers schema


class SmsProviderRoute(Base):
    __tablename__ = "sms_provider_routes"
    __table_args__ = ({"schema": "providers"},)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    organization_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tenancy.organizations.id", ondelete="CASCADE"), nullable=True
    )
    country_code: Mapped[str] = mapped_column(String(4), default="55", nullable=False)
    primary_provider: Mapped[str] = mapped_column(String(64), default="zenvia", nullable=False)
    fallback_provider: Mapped[str | None] = mapped_column(String(64), default="totalvoice", nullable=True)
    max_rps: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


# ============================================================ api_tokens (beacon schema)


class ApiToken(Base):
    __tablename__ = "api_tokens"
    __table_args__ = (
        Index("ix_api_tokens_prefix", "token_prefix"),
        Index("ix_api_tokens_org_active", "organization_id", "revoked_at"),
        {"schema": "beacon"},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenancy.organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    token_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSON, default=lambda: ["messages:write"], nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tenancy.users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


__all__ = [
    "ApiToken",
    "Base",
    "Channel",
    "DedicatedIp",
    "Delivery",
    "EmailDomain",
    "EmailTemplate",
    "Membership",
    "Notification",
    "Organization",
    "PushApp",
    "PushTemplate",
    "SmsProviderRoute",
    "SmsTemplate",
    "SuppressionEntry",
    "Template",
    "Tenant",
    "User",
    "WebhookDelivery",
    "WebhookEndpoint",
    "WhatsappNumber",
]

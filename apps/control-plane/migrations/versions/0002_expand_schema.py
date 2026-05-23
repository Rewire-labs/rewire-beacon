"""Expand BEACON schema for production-grade multi-canal.

Adds 10+ tables in dedicated schemas:
- tenancy.organizations + users + memberships
- senders.email_domains + dedicated_ips + whatsapp_numbers + push_apps
- templates.email_templates + sms_templates + push_templates (richer cols)
- suppression.entries (cross-canal, critical index for <2ms lookup)
- webhooks.endpoints + webhooks.deliveries
- providers.sms_provider_routes
- api_tokens (per organization, bcrypt hashed)

All multi-tenant tables include organization_id for future RLS (BCN-011).

Revision ID: 0002_expand_schema
Revises: 0001_initial
Create Date: 2026-05-23
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_expand_schema"
down_revision: str | Sequence[str] | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SCHEMAS = ["tenancy", "senders", "templates", "suppression", "webhooks", "providers"]


def upgrade() -> None:
    # pgcrypto for gen_random_uuid()
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    for s in SCHEMAS:
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {s}")

    # ---------------------------------------------------------------- tenancy
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("slug", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("tier", sa.String(length=32), nullable=False, server_default="hobby"),
        sa.Column("monthly_quota_email", sa.Integer, nullable=False, server_default="5000"),
        sa.Column("monthly_quota_sms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("monthly_quota_push", sa.Integer, nullable=False, server_default="0"),
        sa.Column("monthly_quota_whatsapp", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("tier IN ('hobby','starter','scale','enterprise')", name="ck_org_tier"),
        sa.CheckConstraint("status IN ('active','suspended','deleted')", name="ck_org_status"),
        schema="tenancy",
    )

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("subject", sa.String(length=255), nullable=True, comment="Authentik OIDC sub"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="tenancy",
    )

    op.create_table(
        "memberships",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="member"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["tenancy.organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["tenancy.users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_membership_org_user"),
        sa.CheckConstraint("role IN ('owner','admin','member','viewer')", name="ck_membership_role"),
        schema="tenancy",
    )

    # ---------------------------------------------------------------- senders
    op.create_table(
        "email_domains",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("verified", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("dkim_public_key", sa.Text, nullable=True),
        sa.Column("dkim_selector", sa.String(length=64), nullable=False, server_default="beacon"),
        sa.Column("spf_status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("dmarc_status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("reputation_score", sa.Integer, nullable=False, server_default="50"),
        sa.Column("postal_vhost_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["tenancy.organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", "domain", name="uq_email_domain_org"),
        sa.CheckConstraint("spf_status IN ('pending','pass','fail','soft_fail','neutral')", name="ck_spf_status"),
        sa.CheckConstraint("dmarc_status IN ('pending','pass','fail','quarantine','reject')", name="ck_dmarc_status"),
        sa.CheckConstraint("reputation_score >= 0 AND reputation_score <= 100", name="ck_reputation_range"),
        schema="senders",
    )
    op.create_index("ix_email_domains_org", "email_domains", ["organization_id"], schema="senders")

    op.create_table(
        "dedicated_ips",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), nullable=True, comment="NULL = shared pool"),
        sa.Column("ip_address", sa.String(length=45), nullable=False, unique=True),
        sa.Column("ptr_record", sa.String(length=255), nullable=True),
        sa.Column("warmup_status", sa.String(length=32), nullable=False, server_default="cold"),
        sa.Column("warmup_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("warmup_target_daily", sa.Integer, nullable=False, server_default="50000"),
        sa.Column("current_daily_cap", sa.Integer, nullable=False, server_default="100"),
        sa.Column("reputation_score", sa.Integer, nullable=False, server_default="50"),
        sa.Column("postal_node", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["tenancy.organizations.id"], ondelete="SET NULL"),
        sa.CheckConstraint("warmup_status IN ('cold','warming','warm','blocked')", name="ck_warmup_status"),
        schema="senders",
    )

    op.create_table(
        "whatsapp_numbers",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("phone_e164", sa.String(length=20), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=True),
        sa.Column("connect_number_id", sa.String(length=128), nullable=True, comment="Mirror from CONNECT"),
        sa.Column("quality_rating", sa.String(length=16), nullable=False, server_default="unknown"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["tenancy.organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", "phone_e164", name="uq_whatsapp_org_phone"),
        sa.CheckConstraint("quality_rating IN ('unknown','green','yellow','red')", name="ck_wa_quality"),
        sa.CheckConstraint("status IN ('pending','approved','suspended','removed')", name="ck_wa_status"),
        schema="senders",
    )

    op.create_table(
        "push_apps",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("platform", sa.String(length=16), nullable=False),
        sa.Column("bundle_id", sa.String(length=255), nullable=True),
        sa.Column("apns_cert_vault_path", sa.String(length=512), nullable=True),
        sa.Column("apns_key_id", sa.String(length=64), nullable=True),
        sa.Column("apns_team_id", sa.String(length=64), nullable=True),
        sa.Column("fcm_service_account_vault_path", sa.String(length=512), nullable=True),
        sa.Column("vapid_public_key", sa.Text, nullable=True),
        sa.Column("vapid_private_key_vault_path", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["tenancy.organizations.id"], ondelete="CASCADE"),
        sa.CheckConstraint("platform IN ('ios','android','web')", name="ck_push_platform"),
        schema="senders",
    )

    # -------------------------------------------------------------- templates
    op.create_table(
        "email_templates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=512), nullable=False),
        sa.Column("mjml_source", sa.Text, nullable=False),
        sa.Column("text_source", sa.Text, nullable=True),
        sa.Column("variables_schema", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["tenancy.organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", "slug", "version", name="uq_email_tpl_org_slug_ver"),
        schema="templates",
    )

    op.create_table(
        "sms_templates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("variables_schema", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["tenancy.organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", "slug", "version", name="uq_sms_tpl_org_slug_ver"),
        schema="templates",
    )

    op.create_table(
        "push_templates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("image_url", sa.String(length=1024), nullable=True),
        sa.Column("click_action", sa.String(length=1024), nullable=True),
        sa.Column("data_payload", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("variables_schema", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["tenancy.organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", "slug", "version", name="uq_push_tpl_org_slug_ver"),
        schema="templates",
    )

    # ------------------------------------------------------------ suppression
    op.create_table(
        "entries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("identifier_type", sa.String(length=16), nullable=False),
        sa.Column("identifier_value", sa.String(length=512), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("source_channel", sa.String(length=32), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["tenancy.organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", "identifier_type", "identifier_value", name="uq_suppression_lookup"),
        sa.CheckConstraint("identifier_type IN ('email','phone_e164','push_token','device_id')", name="ck_suppr_type"),
        sa.CheckConstraint(
            "reason IN ('hard_bounce','complaint','unsubscribe','manual','dsar','invalid','blocked')",
            name="ck_suppr_reason",
        ),
        schema="suppression",
    )
    # critical lookup index — <2ms hot path
    op.create_index(
        "ix_suppression_lookup",
        "entries",
        ["organization_id", "identifier_type", "identifier_value"],
        schema="suppression",
        unique=True,
    )

    # --------------------------------------------------------------- webhooks
    op.create_table(
        "endpoints",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("event_types", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("signing_secret_vault_path", sa.String(length=512), nullable=False),
        sa.Column("max_retries", sa.Integer, nullable=False, server_default="8"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["tenancy.organizations.id"], ondelete="CASCADE"),
        schema="webhooks",
    )
    op.create_index("ix_webhooks_endpoints_org", "endpoints", ["organization_id"], schema="webhooks")

    op.create_table(
        "deliveries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("endpoint_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("http_status", sa.Integer, nullable=True),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["endpoint_id"], ["webhooks.endpoints.id"], ondelete="CASCADE"),
        sa.CheckConstraint("status IN ('pending','delivered','failed','retrying','dead')", name="ck_wh_delivery_status"),
        schema="webhooks",
    )
    op.create_index(
        "ix_webhooks_deliveries_pending",
        "deliveries",
        ["status", "next_attempt_at"],
        schema="webhooks",
    )

    # -------------------------------------------------------------- providers
    op.create_table(
        "sms_provider_routes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), nullable=True, comment="NULL = global default"),
        sa.Column("country_code", sa.String(length=4), nullable=False, server_default="55"),
        sa.Column("primary_provider", sa.String(length=64), nullable=False, server_default="zenvia"),
        sa.Column("fallback_provider", sa.String(length=64), nullable=True, server_default="totalvoice"),
        sa.Column("max_rps", sa.Integer, nullable=False, server_default="10"),
        sa.Column("priority", sa.Integer, nullable=False, server_default="100"),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["tenancy.organizations.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "primary_provider IN ('zenvia','totalvoice','twilio')", name="ck_sms_primary"
        ),
        schema="providers",
    )

    # ------------------------------------------------------------ api_tokens
    op.create_table(
        "api_tokens",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("token_prefix", sa.String(length=16), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("scopes", sa.JSON, nullable=False, server_default='["messages:write"]'),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["tenancy.organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["tenancy.users.id"], ondelete="SET NULL"),
        schema="beacon",
    )
    op.create_index("ix_api_tokens_prefix", "api_tokens", ["token_prefix"], schema="beacon")
    op.create_index("ix_api_tokens_org_active", "api_tokens", ["organization_id", "revoked_at"], schema="beacon")


def downgrade() -> None:
    op.drop_index("ix_api_tokens_org_active", table_name="api_tokens", schema="beacon")
    op.drop_index("ix_api_tokens_prefix", table_name="api_tokens", schema="beacon")
    op.drop_table("api_tokens", schema="beacon")

    op.drop_table("sms_provider_routes", schema="providers")

    op.drop_index("ix_webhooks_deliveries_pending", table_name="deliveries", schema="webhooks")
    op.drop_table("deliveries", schema="webhooks")
    op.drop_index("ix_webhooks_endpoints_org", table_name="endpoints", schema="webhooks")
    op.drop_table("endpoints", schema="webhooks")

    op.drop_index("ix_suppression_lookup", table_name="entries", schema="suppression")
    op.drop_table("entries", schema="suppression")

    op.drop_table("push_templates", schema="templates")
    op.drop_table("sms_templates", schema="templates")
    op.drop_table("email_templates", schema="templates")

    op.drop_table("push_apps", schema="senders")
    op.drop_table("whatsapp_numbers", schema="senders")
    op.drop_table("dedicated_ips", schema="senders")
    op.drop_index("ix_email_domains_org", table_name="email_domains", schema="senders")
    op.drop_table("email_domains", schema="senders")

    op.drop_table("memberships", schema="tenancy")
    op.drop_table("users", schema="tenancy")
    op.drop_table("organizations", schema="tenancy")

    for s in reversed(["tenancy", "senders", "templates", "suppression", "webhooks", "providers"]):
        op.execute(f"DROP SCHEMA IF EXISTS {s} CASCADE")

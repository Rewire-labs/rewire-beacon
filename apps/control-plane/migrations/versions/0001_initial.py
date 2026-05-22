"""Initial BEACON schema (V0 skeleton).

Creates the `beacon` schema and core tables: tenants, channels, templates,
notifications, deliveries. Aligned with src/beacon/db/models.py.

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-21
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS beacon")

    op.create_table(
        "tenants",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("slug", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        schema="beacon",
    )

    op.create_table(
        "channels",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("config", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["beacon.tenants.id"], ondelete="CASCADE"
        ),
        schema="beacon",
    )
    op.create_index(
        "ix_channels_tenant_kind",
        "channels",
        ["tenant_id", "kind"],
        schema="beacon",
    )

    op.create_table(
        "templates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("channel_kind", sa.String(length=32), nullable=False),
        sa.Column("subject", sa.String(length=512), nullable=True),
        sa.Column("body_source", sa.Text, nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["beacon.tenants.id"], ondelete="CASCADE"
        ),
        schema="beacon",
    )
    op.create_index(
        "ix_templates_tenant_slug",
        "templates",
        ["tenant_id", "slug"],
        schema="beacon",
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("template_id", sa.String(length=36), nullable=True),
        sa.Column("channel_kind", sa.String(length=32), nullable=False),
        sa.Column("recipient", sa.String(length=512), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("consent_basis", sa.String(length=64), nullable=True),
        sa.Column("audit_chain_hash", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["beacon.tenants.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["template_id"], ["beacon.templates.id"], ondelete="SET NULL"
        ),
        schema="beacon",
    )
    op.create_index(
        "ix_notifications_tenant_created",
        "notifications",
        ["tenant_id", "created_at"],
        schema="beacon",
    )

    op.create_table(
        "deliveries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("notification_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["notification_id"], ["beacon.notifications.id"], ondelete="CASCADE"
        ),
        schema="beacon",
    )
    op.create_index(
        "ix_deliveries_notification",
        "deliveries",
        ["notification_id"],
        schema="beacon",
    )


def downgrade() -> None:
    op.drop_index("ix_deliveries_notification", table_name="deliveries", schema="beacon")
    op.drop_table("deliveries", schema="beacon")
    op.drop_index(
        "ix_notifications_tenant_created", table_name="notifications", schema="beacon"
    )
    op.drop_table("notifications", schema="beacon")
    op.drop_index("ix_templates_tenant_slug", table_name="templates", schema="beacon")
    op.drop_table("templates", schema="beacon")
    op.drop_index("ix_channels_tenant_kind", table_name="channels", schema="beacon")
    op.drop_table("channels", schema="beacon")
    op.drop_table("tenants", schema="beacon")
    op.execute("DROP SCHEMA IF EXISTS beacon CASCADE")

"""Create `beacon_worker` role with BYPASSRLS for background workers.

Workers (Kafka consumers, Temporal activities, cleanup jobs) need to read
across all tenants without the GUC-based RLS dance. They authenticate as
`beacon_worker` which has BYPASSRLS.

The DDL is idempotent: skip if role exists, ALTER if attributes drift.

Revision ID: 0004_beacon_worker_role
Revises: 0003_rls_force
Create Date: 2026-05-23
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004_beacon_worker_role"
down_revision: str | Sequence[str] | None = "0003_rls_force"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SCHEMAS_READ = ["beacon", "tenancy", "senders", "templates", "suppression", "webhooks", "providers"]


def upgrade() -> None:
    # Create role idempotently — Alembic does not have role helpers, so DO block.
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'beacon_worker') THEN
            CREATE ROLE beacon_worker WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
              NOINHERIT BYPASSRLS;
          ELSE
            ALTER ROLE beacon_worker BYPASSRLS;
          END IF;
        END $$;
        """
    )

    # Grant schema USAGE + table privileges.
    for schema in SCHEMAS_READ:
        op.execute(f"GRANT USAGE ON SCHEMA {schema} TO beacon_worker")
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {schema} TO beacon_worker")
        op.execute(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} "
            "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO beacon_worker"
        )
        op.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {schema} TO beacon_worker")
        op.execute(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT USAGE, SELECT ON SEQUENCES TO beacon_worker"
        )


def downgrade() -> None:
    for schema in SCHEMAS_READ:
        op.execute(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} "
            "REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM beacon_worker"
        )
        op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA {schema} FROM beacon_worker")
        op.execute(f"REVOKE USAGE ON SCHEMA {schema} FROM beacon_worker")
    op.execute("DROP ROLE IF EXISTS beacon_worker")

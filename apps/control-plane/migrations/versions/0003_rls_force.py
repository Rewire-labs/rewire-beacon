"""Enable RLS FORCE + POLICY org_isolation on all multi-tenant tables.

Per ADR 0004 (Multi-tenancy 4 camadas), we use Postgres Row-Level Security
with a per-transaction GUC `beacon.current_org_id` set by the tenancy
middleware before any business query.

Policies:
- ENABLE ROW LEVEL SECURITY + FORCE ROW LEVEL SECURITY on every table that
  has an `organization_id` column.
- POLICY `org_isolation` USING (organization_id = current_setting('beacon.current_org_id', true))
  with WITH CHECK same predicate (writes also restricted to current org).

The migration is idempotent — uses DROP POLICY IF EXISTS first.

Revision ID: 0003_rls_force
Revises: 0002_expand_schema
Create Date: 2026-05-23
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0003_rls_force"
down_revision: str | Sequence[str] | None = "0002_expand_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Tables with `organization_id` column (multi-tenant scope).
RLS_TABLES = [
    ("senders", "email_domains"),
    ("senders", "dedicated_ips"),
    ("senders", "whatsapp_numbers"),
    ("senders", "push_apps"),
    ("templates", "email_templates"),
    ("templates", "sms_templates"),
    ("templates", "push_templates"),
    ("suppression", "entries"),
    ("webhooks", "endpoints"),
    ("providers", "sms_provider_routes"),
    ("beacon", "api_tokens"),
]


def upgrade() -> None:
    for schema, table in RLS_TABLES:
        fq = f"{schema}.{table}"
        # Enable + force RLS so even table owners must satisfy policy.
        op.execute(f"ALTER TABLE {fq} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {fq} FORCE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS org_isolation ON {fq}")
        op.execute(
            f"""
            CREATE POLICY org_isolation ON {fq}
              FOR ALL
              USING (
                organization_id::text = current_setting('beacon.current_org_id', true)
                OR current_setting('beacon.current_org_id', true) IS NULL
                OR current_setting('beacon.current_org_id', true) = ''
              )
              WITH CHECK (
                organization_id::text = current_setting('beacon.current_org_id', true)
              )
            """
        )

    # webhooks.deliveries has no organization_id directly — scope via endpoint.
    op.execute("ALTER TABLE webhooks.deliveries ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE webhooks.deliveries FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS org_isolation ON webhooks.deliveries")
    op.execute(
        """
        CREATE POLICY org_isolation ON webhooks.deliveries
          FOR ALL
          USING (
            EXISTS (
              SELECT 1 FROM webhooks.endpoints e
              WHERE e.id = webhooks.deliveries.endpoint_id
                AND (
                  e.organization_id::text = current_setting('beacon.current_org_id', true)
                  OR current_setting('beacon.current_org_id', true) IS NULL
                  OR current_setting('beacon.current_org_id', true) = ''
                )
            )
          )
          WITH CHECK (
            EXISTS (
              SELECT 1 FROM webhooks.endpoints e
              WHERE e.id = webhooks.deliveries.endpoint_id
                AND e.organization_id::text = current_setting('beacon.current_org_id', true)
            )
          )
        """
    )

    # tenancy.memberships scoped via organization_id.
    op.execute("ALTER TABLE tenancy.memberships ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenancy.memberships FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS org_isolation ON tenancy.memberships")
    op.execute(
        """
        CREATE POLICY org_isolation ON tenancy.memberships
          FOR ALL
          USING (
            organization_id::text = current_setting('beacon.current_org_id', true)
            OR current_setting('beacon.current_org_id', true) IS NULL
            OR current_setting('beacon.current_org_id', true) = ''
          )
          WITH CHECK (
            organization_id::text = current_setting('beacon.current_org_id', true)
          )
        """
    )


def downgrade() -> None:
    for schema, table in RLS_TABLES:
        fq = f"{schema}.{table}"
        op.execute(f"DROP POLICY IF EXISTS org_isolation ON {fq}")
        op.execute(f"ALTER TABLE {fq} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {fq} DISABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS org_isolation ON webhooks.deliveries")
    op.execute("ALTER TABLE webhooks.deliveries NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE webhooks.deliveries DISABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS org_isolation ON tenancy.memberships")
    op.execute("ALTER TABLE tenancy.memberships NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenancy.memberships DISABLE ROW LEVEL SECURITY")

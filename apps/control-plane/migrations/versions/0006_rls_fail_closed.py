"""RW-MESSAGING-03: make RLS org_isolation fail-CLOSED on an empty/unset GUC.

The 0003 policies had a permissive escape hatch in the USING clause::

    organization_id::text = current_setting('beacon.current_org_id', true)
    OR current_setting('beacon.current_org_id', true) IS NULL
    OR current_setting('beacon.current_org_id', true) = ''

An unset GUC makes ``current_setting(..., true)`` return ``''`` -> the
``= ''`` branch is TRUE for EVERY row -> the policy degrades to "expose all
tenants" instead of "expose none". Any code path using a plain ``app_session()``
(or a session where ``set_config`` silently failed) read across tenants.

This migration recreates ``org_isolation`` on every multi-tenant table with a
strict predicate::

    organization_id::text = current_setting('beacon.current_org_id', true)

With the GUC unset, ``current_setting`` returns ``''`` and the comparison is
FALSE for all real (UUID) rows -> zero rows (fail-closed). The WITH CHECK
clause was already strict; it is kept as-is.

GUC NAME: we deliberately keep ``beacon.current_org_id`` (not the canonical
``app.tenant_id`` of ADR0072). This is the documented intra-product exception
for rewire-messaging in the GUC-drift ledger — the entire product (session
factory + tenancy middleware) is consistent on this name, and renaming is a
separate B-class cluster-wide sweep.

Revision ID: 0006_rls_fail_closed
Revises: 0005_pgmq_queues
Create Date: 2026-05-29
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0006_rls_fail_closed"
down_revision: str | Sequence[str] | None = "0005_pgmq_queues"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_GUC = "beacon.current_org_id"

# Mirror of 0003 RLS_TABLES (tables with a direct organization_id column).
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
    ("tenancy", "memberships"),
]


def _direct_policy(fq: str, strict: bool) -> str:
    if strict:
        using = f"organization_id::text = current_setting('{_GUC}', true)"
    else:
        using = (
            f"organization_id::text = current_setting('{_GUC}', true)\n"
            f"            OR current_setting('{_GUC}', true) IS NULL\n"
            f"            OR current_setting('{_GUC}', true) = ''"
        )
    return f"""
        DROP POLICY IF EXISTS org_isolation ON {fq};
        CREATE POLICY org_isolation ON {fq}
          FOR ALL
          USING (
            {using}
          )
          WITH CHECK (
            organization_id::text = current_setting('{_GUC}', true)
          )
    """


def _deliveries_policy(strict: bool) -> str:
    if strict:
        org_pred = f"e.organization_id::text = current_setting('{_GUC}', true)"
    else:
        org_pred = (
            f"e.organization_id::text = current_setting('{_GUC}', true)\n"
            f"                OR current_setting('{_GUC}', true) IS NULL\n"
            f"                OR current_setting('{_GUC}', true) = ''"
        )
    return f"""
        DROP POLICY IF EXISTS org_isolation ON webhooks.deliveries;
        CREATE POLICY org_isolation ON webhooks.deliveries
          FOR ALL
          USING (
            EXISTS (
              SELECT 1 FROM webhooks.endpoints e
              WHERE e.id = webhooks.deliveries.endpoint_id
                AND ({org_pred})
            )
          )
          WITH CHECK (
            EXISTS (
              SELECT 1 FROM webhooks.endpoints e
              WHERE e.id = webhooks.deliveries.endpoint_id
                AND e.organization_id::text = current_setting('{_GUC}', true)
            )
          )
    """


def upgrade() -> None:
    for schema, table in RLS_TABLES:
        op.execute(_direct_policy(f"{schema}.{table}", strict=True))
    op.execute(_deliveries_policy(strict=True))


def downgrade() -> None:
    # Restore the (insecure) permissive 0003 policies.
    for schema, table in RLS_TABLES:
        op.execute(_direct_policy(f"{schema}.{table}", strict=False))
    op.execute(_deliveries_policy(strict=False))

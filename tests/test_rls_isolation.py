"""Tests for RLS cross-tenant isolation.

Integration tests requiring a real Postgres. Skipped automatically if
DATABASE_URL env not set to a postgres URL (CI provides via docker-compose).

Validates POLICY org_isolation on:
- senders.email_domains
- senders.dedicated_ips
- senders.whatsapp_numbers
- senders.push_apps
- templates.email_templates
- templates.sms_templates
- templates.push_templates
- suppression.entries
- webhooks.endpoints
- providers.sms_provider_routes
- beacon.api_tokens

Each table: insert as org A, SET GUC to org B, expect 0 rows visible.
"""
from __future__ import annotations

import os
import uuid

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("BEACON_DATABASE_URL", "").startswith("postgresql"),
    reason="RLS tests need a real Postgres (set BEACON_DATABASE_URL=postgresql+asyncpg://...)",
)


@pytest.fixture
async def two_orgs():
    """Create two orgs in tenancy.organizations and yield (org_a_id, org_b_id)."""
    from sqlalchemy import text

    from beacon.db.session import worker_session

    org_a = str(uuid.uuid4())
    org_b = str(uuid.uuid4())
    async with worker_session() as session:
        await session.execute(
            text(
                "INSERT INTO tenancy.organizations (id, slug, name, tier) "
                "VALUES (:a, :sa, 'Org A', 'hobby'), (:b, :sb, 'Org B', 'hobby')"
            ).bindparams(a=org_a, sa=f"a-{org_a[:8]}", b=org_b, sb=f"b-{org_b[:8]}")
        )
        await session.commit()
    yield org_a, org_b
    async with worker_session() as session:
        await session.execute(
            text("DELETE FROM tenancy.organizations WHERE id IN (:a, :b)").bindparams(a=org_a, b=org_b)
        )
        await session.commit()


@pytest.mark.parametrize(
    "schema,table,extra_cols",
    [
        ("senders", "email_domains", {"domain": "example.test"}),
        ("senders", "dedicated_ips", {"ip_address": "1.2.3.4"}),
        ("senders", "whatsapp_numbers", {"phone_e164": "+5511999990001"}),
        ("senders", "push_apps", {"name": "MyApp", "platform": "ios"}),
        ("templates", "email_templates", {"slug": "t1", "name": "T1", "subject": "S", "mjml_source": "<mjml/>"}),
        ("templates", "sms_templates", {"slug": "t1", "name": "T1", "body": "hi"}),
        ("templates", "push_templates", {"slug": "t1", "name": "T1", "title": "T", "body": "B"}),
        ("suppression", "entries", {"identifier_type": "email", "identifier_value": "x@example.test", "reason": "manual"}),
        ("webhooks", "endpoints", {"url": "https://x.test/hook", "signing_secret_vault_path": "vault/x"}),
        ("providers", "sms_provider_routes", {}),
        ("beacon", "api_tokens", {"name": "t", "token_prefix": "bcn_live_xxxxx", "token_hash": "h"}),
    ],
)
@pytest.mark.asyncio
async def test_rls_blocks_cross_tenant_select(two_orgs, schema, table, extra_cols) -> None:
    from sqlalchemy import text

    from beacon.db.session import worker_session, tenant_scoped_session

    org_a, org_b = two_orgs
    row_id = str(uuid.uuid4())
    cols = {"id": row_id, "organization_id": org_a, **extra_cols}
    col_names = ",".join(cols.keys())
    placeholders = ",".join(f":{k}" for k in cols.keys())
    # Use worker (BYPASSRLS) to insert as org_a.
    async with worker_session() as s:
        await s.execute(text(f"INSERT INTO {schema}.{table} ({col_names}) VALUES ({placeholders})").bindparams(**cols))
        await s.commit()
    # Now SET GUC to org_b and expect 0 visible.
    async with tenant_scoped_session(org_b) as s:
        result = await s.execute(text(f"SELECT id FROM {schema}.{table} WHERE id = :id").bindparams(id=row_id))
        assert result.first() is None, f"RLS failed: org_b saw row from org_a in {schema}.{table}"
    # Cleanup.
    async with worker_session() as s:
        await s.execute(text(f"DELETE FROM {schema}.{table} WHERE id = :id").bindparams(id=row_id))
        await s.commit()


@pytest.mark.asyncio
async def test_rls_fail_closed_without_guc(two_orgs) -> None:
    """RW-MESSAGING-03: a session with NO GUC set must see ZERO rows.

    The old 0003 policy exposed ALL rows when the GUC was empty; 0006 makes it
    fail-closed. We insert a row via the BYPASSRLS worker role, then read it
    back through a plain RLS-bound ``app_session`` (no SET GUC) and assert it
    is invisible.
    """
    from sqlalchemy import text

    from beacon.db.session import app_session, worker_session

    org_a, _org_b = two_orgs
    row_id = str(uuid.uuid4())
    async with worker_session() as s:
        await s.execute(
            text(
                "INSERT INTO senders.email_domains (id, organization_id, domain) "
                "VALUES (:id, :org, :dom)"
            ).bindparams(id=row_id, org=org_a, dom="failclosed.test")
        )
        await s.commit()
    try:
        async with app_session() as s:
            result = await s.execute(
                text("SELECT id FROM senders.email_domains WHERE id = :id").bindparams(
                    id=row_id
                )
            )
            assert result.first() is None, (
                "RLS NOT fail-closed: empty GUC exposed a row (0003 bypass regression)"
            )
    finally:
        async with worker_session() as s:
            await s.execute(
                text("DELETE FROM senders.email_domains WHERE id = :id").bindparams(
                    id=row_id
                )
            )
            await s.commit()

"""RW-MESSAGING-04 — DSAR export/redact hit the REAL beacon.* schema.

The previous queries targeted a nonexistent ``messaging.*`` schema with
columns that don't exist, so every query fell into a bare except and the
export silently returned ``record_counts={}`` (an LGPD Art. 18 breach: the
operator believed the subject had no data).

These tests seed a tenant + notification + delivery + suppression entry into
an in-memory sqlite (schemas mapped via ATTACH) and assert the exporter
returns REAL counts and the deleter redacts the recipient PII.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

_SCHEMAS = ("beacon", "tenancy", "senders", "templates", "suppression", "webhooks", "providers")


@pytest.fixture
async def seeded_session_ctx():
    """Yield a worker_session-shaped context bound to a seeded sqlite db."""
    from beacon.db.models import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    # sqlite has no schemas — ATTACH one in-memory db per schema name. The
    # ATTACH must persist for the connection lifetime, so we keep a single
    # connection and build the sessionmaker bound to it.
    raw = await engine.connect()
    for s in _SCHEMAS:
        await raw.exec_driver_sql(f"ATTACH DATABASE ':memory:' AS {s}")
    await raw.run_sync(lambda c: Base.metadata.create_all(c))
    await raw.commit()

    # Seed data via exec_driver_sql so the JSON literal's ``:`` is not parsed
    # as a SQLAlchemy bind parameter.
    await raw.exec_driver_sql(
        "INSERT INTO beacon.tenants (id, slug, name, created_at, active) "
        "VALUES ('t1','s1','Tenant 1','2026-01-01', 1)"
    )
    await raw.exec_driver_sql(
        "INSERT INTO beacon.notifications "
        "(id, tenant_id, channel_kind, recipient, payload, consent_basis, created_at) "
        "VALUES ('n1','t1','email','alice@example.com','{\"x\":1}','contract','2026-01-02')"
    )
    await raw.exec_driver_sql(
        "INSERT INTO beacon.deliveries "
        "(id, notification_id, provider, status, attempts, created_at) "
        "VALUES ('d1','n1','postal','delivered',1,'2026-01-02')"
    )
    await raw.exec_driver_sql(
        "INSERT INTO suppression.entries "
        "(id, organization_id, identifier_type, identifier_value, reason, created_at) "
        "VALUES ('e1','t1','email','alice@example.com','bounce','2026-01-02')"
    )
    await raw.commit()

    sm = async_sessionmaker(bind=raw, expire_on_commit=False)

    @asynccontextmanager
    async def _ctx():
        async with sm() as session:
            yield session

    yield _ctx, raw
    await raw.close()
    await engine.dispose()


@pytest.mark.unit
async def test_export_returns_real_counts(seeded_session_ctx, monkeypatch):
    ctx_factory, _raw = seeded_session_ctx
    import beacon.api.internal_dsar as mod

    monkeypatch.setattr(mod, "_session_ctx", lambda: ctx_factory)

    from rewire_shared.lgpd_dsar import DSARExporterContext

    class _Req:
        tenant_id = "t1"
        subject_email = "alice@example.com"

    artifact = await mod.MessagingTenantDataExporter().export(
        DSARExporterContext(request=_Req(), product_slug="rewire-messaging", matched_audit_secret_id="current")
    )
    counts = artifact.record_counts
    assert counts.get("notifications") == 1, counts
    assert counts.get("deliveries") == 1, counts
    assert counts.get("suppression_entries") == 1, counts
    assert artifact.payload is not None
    assert artifact.payload["tables"]["notifications"][0]["channel_kind"] == "email"


@pytest.mark.unit
async def test_delete_redacts_recipient_and_drops_suppression(seeded_session_ctx, monkeypatch):
    ctx_factory, raw = seeded_session_ctx
    import beacon.api.internal_dsar as mod

    monkeypatch.setattr(mod, "_session_ctx", lambda: ctx_factory)

    from rewire_shared.lgpd_dsar import DSARDeleterContext

    class _Req:
        tenant_id = "t1"
        subject_email = "alice@example.com"

    outcome = await mod.MessagingTenantDataDeleter().delete(
        DSARDeleterContext(request=_Req(), product_slug="rewire-messaging", matched_audit_secret_id="current")
    )
    assert outcome.tombstoned.get("suppression_entries") == 1, outcome.tombstoned
    assert outcome.retained_under_legal_basis.get("notifications") == 1, outcome.retained_under_legal_basis

    # Recipient is redacted; suppression entry is gone.
    row = (await raw.execute(text("SELECT recipient, payload FROM beacon.notifications WHERE id='n1'"))).first()
    assert row[0].startswith("redacted-")
    assert "@deleted.invalid" in row[0]
    supp = (await raw.execute(text("SELECT count(*) FROM suppression.entries WHERE identifier_value='alice@example.com'"))).scalar()
    assert supp == 0

"""RW-MESSAGING-03 — RLS policies are fail-closed; GUC set failures raise.

These are fast unit checks that do not need a live Postgres:
  * migration 0006 must NOT contain the permissive ``IS NULL``/``= ''`` bypass
    in its upgrade() output;
  * ``tenant_scoped_session`` must propagate a ``set_config`` failure on a
    non-sqlite backend (no silent empty-GUC continuation).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_MIG = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "0006_rls_fail_closed.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("mig_0006", _MIG)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.unit
def test_upgrade_policies_have_no_empty_guc_bypass():
    mod = _load_migration()
    # The strict (upgrade) policy generator must not emit the bypass clauses.
    strict_direct = mod._direct_policy("senders.email_domains", strict=True)
    strict_deliveries = mod._deliveries_policy(strict=True)
    for sql in (strict_direct, strict_deliveries):
        assert "IS NULL" not in sql, "fail-closed policy must not allow NULL GUC"
        assert "= ''" not in sql, "fail-closed policy must not allow empty GUC"
        assert "current_setting('beacon.current_org_id', true)" in sql
    # Sanity: the permissive (downgrade) variant DOES carry the bypass.
    assert "IS NULL" in mod._direct_policy("senders.email_domains", strict=False)


@pytest.mark.unit
def test_all_multitenant_tables_covered():
    mod = _load_migration()
    names = {f"{s}.{t}" for s, t in mod.RLS_TABLES}
    # Must include the tenancy.memberships table 0003 patched separately.
    assert "tenancy.memberships" in names
    assert "beacon.api_tokens" in names
    assert "suppression.entries" in names


@pytest.mark.unit
async def test_tenant_scoped_session_raises_on_set_config_failure(monkeypatch):
    """Non-sqlite backend whose set_config errors must propagate, not swallow."""
    import beacon.db.session as sess

    class _FakeDialect:
        name = "postgresql"

    class _FakeBind:
        dialect = _FakeDialect()

    class _FakeSession:
        bind = _FakeBind()

        async def execute(self, *_a, **_k):
            raise RuntimeError("set_config blew up")

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _fake_app_session():
        yield _FakeSession()

    monkeypatch.setattr(sess, "app_session", _fake_app_session)

    with pytest.raises(RuntimeError, match="set_config blew up"):
        async with sess.tenant_scoped_session("org-1"):
            pass  # pragma: no cover — should not reach


@pytest.mark.unit
async def test_tenant_scoped_session_noops_on_sqlite(monkeypatch):
    import beacon.db.session as sess

    class _FakeDialect:
        name = "sqlite"

    class _FakeBind:
        dialect = _FakeDialect()

    executed: list = []

    class _FakeSession:
        bind = _FakeBind()

        async def execute(self, *a, **k):  # pragma: no cover - should not run
            executed.append((a, k))

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _fake_app_session():
        yield _FakeSession()

    monkeypatch.setattr(sess, "app_session", _fake_app_session)

    async with sess.tenant_scoped_session("org-1") as s:
        assert s is not None
    assert executed == [], "SQLite path must not attempt set_config"

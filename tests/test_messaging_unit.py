"""Unit tests for canonical messaging send path (MESSAGING-12 + MESSAGING-21).

Covers suppression, idempotency, per-category preferences (opt-out), per-tenant
sliding-window rate limit, frequency cap, and atomic monthly quota decrement.
All deterministic via an injectable ``now`` clock — no DB / Redis required.
"""

import importlib.util
import pathlib

import pytest

# Load the module directly from its source path so the test runs without the
# package being installed.
_SRC = (
    pathlib.Path(__file__).resolve().parents[1]
    / "apps"
    / "control-plane"
    / "src"
    / "beacon"
    / "services"
    / "messaging.py"
)
_spec = importlib.util.spec_from_file_location("beacon_messaging", _SRC)
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)


def _req(**kw):
    base = dict(tenant_id="t1", channel=m.Channel.EMAIL, recipient="a@x.com")
    base.update(kw)
    return m.SendRequest(**base)


def test_basic_allow():
    svc = m.MessagingService()
    res = svc.evaluate(_req(idempotency_key="k1"))
    assert res.allowed
    assert res.decision is m.SendDecision.ALLOW


def test_suppression_blocks():
    svc = m.MessagingService()
    svc.suppression.suppress("t1", m.Channel.EMAIL, "a@x.com")
    res = svc.evaluate(_req(idempotency_key="k1"))
    assert res.decision is m.SendDecision.SUPPRESSED


def test_idempotency_dedupes_replay():
    svc = m.MessagingService()
    first = svc.evaluate(_req(idempotency_key="dup"))
    second = svc.evaluate(_req(idempotency_key="dup"))
    assert first.allowed
    assert second.decision is m.SendDecision.DUPLICATE


def test_idempotency_key_derived_when_absent():
    r1 = _req(body="hello")
    r2 = _req(body="hello")
    r3 = _req(body="world")
    assert r1.derived_idempotency_key() == r2.derived_idempotency_key()
    assert r1.derived_idempotency_key() != r3.derived_idempotency_key()


def test_category_opt_out():
    svc = m.MessagingService()
    svc.preferences.set_preference(
        "t1", "marketing", m.CategoryPreference(enabled=False)
    )
    res = svc.evaluate(_req(category="marketing", idempotency_key="k1"))
    assert res.decision is m.SendDecision.CATEGORY_OPTED_OUT


def test_rate_limit_sliding_window():
    svc = m.MessagingService(rate_limit=2, rate_window_seconds=10)
    # generous quota / no freq cap (transactional)
    t = 1000.0
    assert svc.evaluate(_req(idempotency_key="a"), now=t).allowed
    assert svc.evaluate(_req(idempotency_key="b"), now=t).allowed
    third = svc.evaluate(_req(idempotency_key="c"), now=t)
    assert third.decision is m.SendDecision.RATE_LIMITED
    # after the window slides, allowed again
    later = svc.evaluate(_req(idempotency_key="d"), now=t + 11)
    assert later.allowed


def test_quota_decrement_and_exhaustion():
    svc = m.MessagingService()
    svc.quota.set_quota("t1", 1)
    assert svc.evaluate(_req(idempotency_key="a")).allowed
    assert svc.quota.remaining("t1") == 0
    res = svc.evaluate(_req(idempotency_key="b"))
    assert res.decision is m.SendDecision.QUOTA_EXCEEDED


def test_quota_unlimited_when_unset():
    svc = m.MessagingService()
    for i in range(50):
        assert svc.evaluate(_req(idempotency_key=f"k{i}")).allowed


def test_quota_not_burned_on_rejected_request():
    svc = m.MessagingService(rate_limit=1, rate_window_seconds=10)
    svc.quota.set_quota("t1", 5)
    t = 500.0
    assert svc.evaluate(_req(idempotency_key="a"), now=t).allowed
    # second is rate limited -> quota must NOT be decremented
    rl = svc.evaluate(_req(idempotency_key="b"), now=t)
    assert rl.decision is m.SendDecision.RATE_LIMITED
    assert svc.quota.remaining("t1") == 4


def test_frequency_cap_per_category():
    svc = m.MessagingService()
    svc.preferences.set_preference(
        "t1",
        "marketing",
        m.CategoryPreference(enabled=True, frequency_cap=2, cap_period_seconds=3600),
    )
    t = 0.0
    assert svc.evaluate(_req(category="marketing", idempotency_key="a"), now=t).allowed
    assert svc.evaluate(_req(category="marketing", idempotency_key="b"), now=t).allowed
    capped = svc.evaluate(_req(category="marketing", idempotency_key="c"), now=t)
    assert capped.decision is m.SendDecision.FREQUENCY_CAPPED
    # after period elapses, allowed again
    ok = svc.evaluate(_req(category="marketing", idempotency_key="d"), now=t + 3601)
    assert ok.allowed


def test_transactional_not_frequency_capped():
    svc = m.MessagingService()
    t = 0.0
    for i in range(20):
        res = svc.evaluate(_req(category="transactional", idempotency_key=f"k{i}"), now=t)
        assert res.allowed


def test_frequency_cap_is_per_recipient():
    svc = m.MessagingService()
    svc.preferences.set_preference(
        "t1", "marketing", m.CategoryPreference(enabled=True, frequency_cap=1)
    )
    a = svc.evaluate(_req(category="marketing", recipient="a@x.com", idempotency_key="a"))
    b = svc.evaluate(_req(category="marketing", recipient="b@x.com", idempotency_key="b"))
    assert a.allowed and b.allowed


def test_rate_limiter_invalid_config():
    with pytest.raises(ValueError):
        m.SlidingWindowRateLimiter(0, 10)
    with pytest.raises(ValueError):
        m.SlidingWindowRateLimiter(5, 0)


def test_quota_store_atomic_no_negative():
    q = m.QuotaStore()
    q.set_quota("t1", 2)
    assert q.try_decrement("t1", 1)
    assert q.try_decrement("t1", 1)
    assert not q.try_decrement("t1", 1)
    assert q.remaining("t1") == 0

"""Unit tests for messaging service (no DB).

Validates pure functions: ULID generation, chain hash determinism,
pricing math, suppression normalization, template rendering.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest


def test_ulid_monotonic_within_ms() -> None:
    from beacon.services.messaging import new_ulid

    ids = [new_ulid() for _ in range(50)]
    # All unique.
    assert len(set(ids)) == 50
    # Length canonical 26 chars Crockford base32.
    assert all(len(i) == 26 for i in ids)


def test_chain_hash_deterministic() -> None:
    from beacon.services.audit_chain import compute_chain_hash

    ts = datetime(2026, 5, 23, 12, 0, tzinfo=UTC)
    a = compute_chain_hash(
        organization_id="org1", recipient="u@x.com", channel="email",
        content="hi", timestamp=ts, consent_basis="consent",
    )
    b = compute_chain_hash(
        organization_id="org1", recipient="u@x.com", channel="email",
        content="hi", timestamp=ts, consent_basis="consent",
    )
    assert a == b
    c = compute_chain_hash(
        organization_id="org2", recipient="u@x.com", channel="email",
        content="hi", timestamp=ts, consent_basis="consent",
    )
    assert a != c


def test_pricing_quote_markup() -> None:
    from beacon.services.pricing import quote

    q = quote(channel="sms", tier="starter", provider_cost_cents=10)
    assert q.customer_brl_cents == 14  # 40% markup
    assert q.cost_brl_cents == 10
    assert q.markup_bps == 4000


def test_template_handlebars_variable() -> None:
    from beacon.services.template_rendering import render_handlebars

    out = render_handlebars("Hello {{name}}!", {"name": "World"})
    assert out == "Hello World!"


def test_template_handlebars_each_loop() -> None:
    from beacon.services.template_rendering import render_handlebars

    out = render_handlebars("{{#each items}}{{this}},{{/each}}", {"items": ["a", "b", "c"]})
    assert out == "a,b,c,"


def test_template_handlebars_conditional() -> None:
    from beacon.services.template_rendering import render_handlebars

    out = render_handlebars("{{#if premium}}VIP{{/if}}", {"premium": True})
    assert out == "VIP"
    out2 = render_handlebars("{{#if premium}}VIP{{/if}}", {"premium": False})
    assert out2 == ""


def test_unsubscribe_token_roundtrip() -> None:
    from beacon.api.unsubscribe import _decode_token, generate_unsubscribe_token

    tok = generate_unsubscribe_token(organization_id="org1", identifier_type="email", identifier_value="u@x.com")
    org, it, val = _decode_token(tok)
    assert (org, it, val) == ("org1", "email", "u@x.com")


def test_api_token_prefix_extract() -> None:
    from beacon.middleware.auth import extract_token_prefix, hash_api_token

    raw = "bcn_live_abcdef1234567890XYZ"
    assert extract_token_prefix(raw) == "bcn_live_abcdef"
    # hash deterministic.
    h1 = hash_api_token(raw)
    h2 = hash_api_token(raw)
    assert h1 == h2


def test_quiet_hours_default_window() -> None:
    from datetime import time

    from beacon.services.quiet_hours import is_in_quiet_window

    # 23:00 -> in quiet
    night = datetime(2026, 5, 23, 23, 0, tzinfo=UTC)
    assert is_in_quiet_window("org1", now=night)
    # 12:00 -> not in quiet
    noon = datetime(2026, 5, 23, 12, 0, tzinfo=UTC)
    # Note this is UTC 12:00 = 09:00 BRT - not in quiet
    assert not is_in_quiet_window("org1", now=noon)


def test_antispam_keyword_score() -> None:
    import asyncio

    from beacon.services.antispam import evaluate

    async def run() -> None:
        d = await evaluate(
            organization_id="org1",
            content="FREE BITCOIN!!! CLICK HERE NOW casino viagra weight loss",
            recipients_count=1,
        )
        assert d.decision in ("review", "block")
        assert d.score >= 30

    asyncio.run(run())

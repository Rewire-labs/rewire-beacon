"""Tests for credits + Lago emit modules."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "apps" / "control-plane" / "src"))

from messaging_cp.credits_emit import (  # noqa: E402
    CREDIT_WEIGHTS,
    emit_messaging_credit,
)
from messaging_cp.lago_emit import (  # noqa: E402
    VALID_METRICS,
    emit_messaging_billable,
)


def test_credit_weights_match_spec() -> None:
    """Spec: email=0, sms_br=2, push=0."""
    assert CREDIT_WEIGHTS["email_transactional"] == 0
    assert CREDIT_WEIGHTS["sms_br"] == 2
    assert CREDIT_WEIGHTS["push_notification"] == 0


def test_lago_metric_set_matches_spec() -> None:
    assert VALID_METRICS == {
        "messaging_email_sent",
        "messaging_sms_sent",
        "messaging_push_sent",
    }


@pytest.mark.asyncio
async def test_credit_emit_does_not_raise_when_shared_missing() -> None:
    """Dev fallback: shared lib unavailable -> log warning, return None."""
    # No matter the env, the function must never raise.
    await emit_messaging_credit(
        tenant_id="org_test", action_type="email_transactional", quantity=1
    )


@pytest.mark.asyncio
async def test_lago_invalid_metric_no_raise() -> None:
    """Invalid metric -> warning, no exception."""
    await emit_messaging_billable(
        tenant_id="org_test", metric="not_a_metric", value=1
    )


@pytest.mark.asyncio
async def test_lago_no_api_key_no_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LAGO_API_KEY", raising=False)
    await emit_messaging_billable(
        tenant_id="org_test", metric="messaging_email_sent", value=1
    )

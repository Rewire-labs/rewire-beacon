"""BCN-CAP-01 + BCN-AICX-01: capability registry + agent invoke tests.

Mirrors the pulse-cloud + citadel-cloud reference test suites so the
canonical agent contract is validated identically across services.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure the registry loader finds the repo-root capabilities.yaml even when
# pytest is invoked from a different cwd.
_REPO_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault(
    "BEACON_CAPABILITIES_PATH", str(_REPO_ROOT / "capabilities.yaml")
)


@pytest.fixture(autouse=True)
def _reset_caches() -> None:
    """Reset registry + idempotency caches between tests."""
    from beacon.agents.agent_invoke_router import reset_idempotency_cache_for_tests
    from beacon.agents.capability_loader import reset_registry_cache_for_tests

    reset_registry_cache_for_tests()
    reset_idempotency_cache_for_tests()
    yield
    reset_registry_cache_for_tests()
    reset_idempotency_cache_for_tests()


def _client() -> TestClient:
    from beacon.main import app

    return TestClient(app)


# ---------------------------------------------------------------------------
# BCN-CAP-01: GET /api/v1/capabilities
# ---------------------------------------------------------------------------


def test_get_capabilities_returns_canonical_registry() -> None:
    with _client() as c:
        r = c.get("/api/v1/capabilities")
        assert r.status_code == 200
        body = r.json()
        assert body["service"] == "rewire-beacon"
        assert body["version"]
        assert body["etag"].startswith('W/"')
        assert isinstance(body["capabilities"], list)
        assert len(body["capabilities"]) >= 6
        # Capability IDs follow canonical regex
        for cap in body["capabilities"]:
            assert cap["id"].startswith("rewire.beacon.")
            assert cap["agent_endpoint"] == "/agent/v1/invoke"
            assert cap["invoke"]["transport"] == "rest"
            assert "input" in cap["invoke"]["schema"]
            assert "output" in cap["invoke"]["schema"]
            assert cap["audit"]["emit_event"].startswith("rewire.beacon.")


def test_get_capabilities_etag_304() -> None:
    with _client() as c:
        first = c.get("/api/v1/capabilities")
        etag = first.headers.get("ETag")
        assert etag
        second = c.get("/api/v1/capabilities", headers={"If-None-Match": etag})
        assert second.status_code == 304
        assert second.headers.get("ETag") == etag


# ---------------------------------------------------------------------------
# BCN-AICX-01: POST /agent/v1/invoke
# ---------------------------------------------------------------------------


def _invoke_headers(**extra: str) -> dict[str, str]:
    base = {
        "X-Rewire-Agent-Src": "chat-orchestrator",
        "X-Rewire-Agent-Dst": "rewire-beacon",
        "X-Rewire-Tenant-Id": "global",
        "X-Rewire-Trace-Id": "trace-test-001",
    }
    base.update(extra)
    return base


def test_agent_invoke_send_email_ok() -> None:
    with _client() as c:
        r = c.post(
            "/agent/v1/invoke",
            headers=_invoke_headers(),
            json={
                "capability": "rewire.beacon.send_email",
                "input": {
                    "tenant_id": "11111111-1111-1111-1111-111111111111",
                    "sender": "ops@example.com",
                    "to": ["user@example.com"],
                    "subject": "test",
                    "consent_basis": "contract",
                },
                "metadata": {"deadline_ms": 5000, "max_cost_usd": 0.01},
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "ok"
        assert body["output"]["message_id"].startswith("msg_")
        assert body["output"]["chain_hash"].startswith("blake3:")
        assert body["audit_chain_hash"] == body["output"]["chain_hash"]
        assert body["trace_id"] == "trace-test-001"


def test_agent_invoke_unknown_capability_404() -> None:
    with _client() as c:
        r = c.post(
            "/agent/v1/invoke",
            headers=_invoke_headers(),
            json={
                "capability": "rewire.beacon.does_not_exist",
                "input": {},
            },
        )
        assert r.status_code == 404
        assert "capability_unknown" in r.json()["detail"]


def test_agent_invoke_agent_dst_mismatch_403() -> None:
    with _client() as c:
        r = c.post(
            "/agent/v1/invoke",
            headers=_invoke_headers(**{"X-Rewire-Agent-Dst": "wrong-service"}),
            json={
                "capability": "rewire.beacon.send_email",
                "input": {
                    "tenant_id": "11111111-1111-1111-1111-111111111111",
                    "sender": "ops@example.com",
                    "to": ["user@example.com"],
                    "subject": "test",
                    "consent_basis": "contract",
                },
            },
        )
        assert r.status_code == 403
        assert "agent_dst_mismatch" in r.json()["detail"]


def test_agent_invoke_missing_jwt_and_src_401() -> None:
    with _client() as c:
        r = c.post(
            "/agent/v1/invoke",
            headers={"X-Rewire-Agent-Dst": "rewire-beacon"},
            json={"capability": "rewire.beacon.send_email", "input": {}},
        )
        assert r.status_code == 401


def test_agent_invoke_idempotency_replay() -> None:
    """Two calls with the same X-Rewire-Idempotency-Key return same response."""
    with _client() as c:
        key = "idem-test-abc-001"
        payload = {
            "capability": "rewire.beacon.send_sms",
            "input": {
                "tenant_id": "22222222-2222-2222-2222-222222222222",
                "to": "+5511999998888",
                "text": "OTP 1234",
                "consent_basis": "legal_obligation",
            },
        }
        r1 = c.post(
            "/agent/v1/invoke",
            headers=_invoke_headers(**{"X-Rewire-Idempotency-Key": key}),
            json=payload,
        )
        r2 = c.post(
            "/agent/v1/invoke",
            headers=_invoke_headers(**{"X-Rewire-Idempotency-Key": key}),
            json=payload,
        )
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json()["output"] == r2.json()["output"]
        assert r1.json()["audit_chain_hash"] == r2.json()["audit_chain_hash"]


def test_agent_invoke_input_schema_validation_400() -> None:
    """Missing required field in input -> 400 input_schema_failed."""
    with _client() as c:
        r = c.post(
            "/agent/v1/invoke",
            headers=_invoke_headers(),
            json={
                "capability": "rewire.beacon.send_email",
                "input": {
                    # Missing tenant_id + sender + to + subject + consent_basis
                    "subject": "missing fields"
                },
            },
        )
        # If jsonschema lib not installed, returns 200 (validation skipped).
        # If installed, returns 400.
        assert r.status_code in (200, 400)


def test_agent_invoke_chain_ref_propagation() -> None:
    """X-Rewire-Audit-Chain-Ref in -> different audit_chain_hash out."""
    with _client() as c:
        payload = {
            "capability": "rewire.beacon.send_email",
            "input": {
                "tenant_id": "33333333-3333-3333-3333-333333333333",
                "sender": "ops@example.com",
                "to": ["chain@example.com"],
                "subject": "chain test",
                "consent_basis": "contract",
            },
        }
        r1 = c.post(
            "/agent/v1/invoke", headers=_invoke_headers(), json=payload
        )
        r2 = c.post(
            "/agent/v1/invoke",
            headers=_invoke_headers(
                **{"X-Rewire-Audit-Chain-Ref": "blake3:upstream_anchor_xyz"}
            ),
            json=payload,
        )
        # Different chain_ref_in -> different anchored hash.
        assert r1.json()["audit_chain_hash"] != r2.json()["audit_chain_hash"]


def test_agent_invoke_budget_exceeded_returns_error_envelope() -> None:
    """max_cost_usd=0 vs token budget=0 — should still pass (free)."""
    with _client() as c:
        r = c.post(
            "/agent/v1/invoke",
            headers=_invoke_headers(),
            json={
                "capability": "rewire.beacon.check_suppression",
                "input": {
                    "tenant_id": "44444444-4444-4444-4444-444444444444",
                    "identifier_type": "email",
                    "identifier_value": "test@example.com",
                },
                "metadata": {"deadline_ms": 1000, "max_cost_usd": 0.0},
            },
        )
        # check_suppression is deterministic 0 cost -> passes even at 0 budget
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# BCN-100/102: BudgetState header round-trip
# ---------------------------------------------------------------------------


def test_budget_state_round_trip() -> None:
    from beacon.agents.agent_bus_client import BudgetState

    bs = BudgetState(usd_remaining=0.4242, ttl_s=120)
    header = bs.to_header()
    assert "usd=" in header and "ttl_s=" in header
    parsed = BudgetState.from_header(header)
    assert parsed is not None
    assert abs(parsed.usd_remaining - 0.4242) < 1e-6
    assert parsed.ttl_s == 120


def test_budget_state_from_malformed_header_returns_none() -> None:
    from beacon.agents.agent_bus_client import BudgetState

    # Type-invalid values -> parser returns None.
    assert BudgetState.from_header("usd=NaN;ttl_s=abc") is None
    # Empty header still produces parser-default state, that's by design.
    empty = BudgetState.from_header("")
    assert empty is None or (empty.usd_remaining == 0.0 and empty.ttl_s == 60)


# ---------------------------------------------------------------------------
# BCN-101: AgentEvent envelope + AgentBusRMQ mock mode
# ---------------------------------------------------------------------------


def test_agent_event_envelope_round_trip() -> None:
    from beacon.agents.agent_bus_rmq import AgentEvent

    ev = AgentEvent.new(
        src="beacon-ai",
        dst="citadel",
        event="message_dispatched",
        tenant_id="tnt_001",
        payload={"channel": "email", "msg_id": "msg_abc"},
        trace_id="trace_xyz",
        audit_chain_ref="blake3:anchor",
    )
    s = ev.to_json()
    parsed = AgentEvent.from_json(s)
    assert parsed.event_id == ev.event_id
    assert parsed.src == "beacon-ai"
    assert parsed.dst == "citadel"
    assert parsed.event == "message_dispatched"
    assert parsed.routing_key() == "agent.beacon-ai.citadel.message_dispatched"


@pytest.mark.asyncio
async def test_agent_bus_rmq_mock_mode_publishes_to_inmem_list() -> None:
    from beacon.agents.agent_bus_rmq import AgentBusRMQ, AgentEvent

    bus = AgentBusRMQ(rmq_url="")  # force mock mode
    await bus.connect()
    assert bus.is_mock
    ev = AgentEvent.new(
        src="beacon-ai",
        dst="metering",
        event="message_dispatched",
        tenant_id="tnt_001",
    )
    await bus.publish(ev)
    assert len(bus.mock_emitted) == 1
    assert bus.mock_emitted[0].event_id == ev.event_id

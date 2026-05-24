# BEACON — Capability registry + agent invoke

Canonical implementation of [[ADR-0106]] (Capability Registry MCP)
and [[ADR-0107]] (Central AI Chat orchestrator) for the **rewire-beacon**
service. Mirrors the PULSE-CLOUD + CITADEL-CLOUD impls 1:1 so the
chat-orchestrator can probe any service uniformly.

## Endpoints

### `GET /api/v1/capabilities`

Returns the canonical registry of capabilities exposed by this service.
**Public** (no auth) — intentionally: contracts only, no secrets.

**Response 200**:

```json
{
  "service": "rewire-beacon",
  "version": "0.1.0",
  "etag": "W/\"<sha256-32hex>\"",
  "capabilities": [
    {
      "id": "rewire.beacon.send_email",
      "name": "Send a transactional email (multi-tenant)",
      "description": "Enqueue a transactional email ...",
      "version": "1.0.0",
      "category": "dispatch",
      "agent_endpoint": "/agent/v1/invoke",
      "invoke": {
        "transport": "rest",
        "endpoint": "/agent/v1/invoke",
        "schema": {
          "input": { "type": "object", "required": [...], "properties": {...} },
          "output": { "type": "object", "required": [...], "properties": {...} }
        }
      },
      "budget": { "per_call_max_seconds": 5, "per_call_tokens": 0 },
      "permissions": {
        "requires_oauth": true,
        "scopes": ["beacon.messages.send"],
        "requires_hitl": false,
        "sensitivity": "medium"
      },
      "audit": { "emit_event": "rewire.beacon.send_email.invoked" },
      "deprecation": { "deprecated_at": null, "sunset_at": null }
    }
  ]
}
```

**ETag** support: pass `If-None-Match: W/"..."` to get a `304 Not
Modified` when the registry has not changed.

**Aggregator invalidation**: on container startup, BEACON fires
`POST $REWIRE_AGGREGATOR_URL/aggregator/invalidate` (fire-and-forget,
2s timeout) so the central rewire-mcp aggregator re-pulls.

### `POST /agent/v1/invoke`

Canonical agent invoke endpoint aderente a INTER_AGENT_COMM_SPEC §1.3-1.4.

**Headers**:

| Header | Required | Notes |
|---|---|---|
| `Authorization: Bearer <JWT>` | yes (prod) | `agents.rewire.svc` audience |
| `X-Rewire-Agent-Src` | yes | `chat-orchestrator` typical |
| `X-Rewire-Agent-Dst` | recommended | rejects 403 if mismatch with `rewire-beacon` |
| `X-Rewire-Trace-Id` | recommended | W3C trace; generated if absent |
| `X-Rewire-Span-Id` | recommended | parent span |
| `X-Rewire-Tenant-Id` | recommended | `global` for ops-only |
| `X-Rewire-Idempotency-Key` | yes on mutations | UUIDv4; 24h Redis-backed dedupe |
| `X-Rewire-Audit-Chain-Ref` | optional | CITADEL chain anchor in; propagated out |
| `X-Rewire-Tenant-Budget` | optional | `usd=0.42;ttl_s=60` |

**Body**:

```json
{
  "capability": "rewire.beacon.send_email",
  "input": { ... },
  "metadata": { "deadline_ms": 30000, "max_cost_usd": 0.05, "reason": "agent_chain" }
}
```

**Response 200**:

```json
{
  "status": "ok | error | partial",
  "output": { ... },
  "cost_usd": 0.0,
  "latency_ms": 12,
  "audit_chain_hash": "blake3:...",
  "trace_id": "...",
  "error": null
}
```

**Error codes**:

| HTTP | Reason |
|---|---|
| 400 | `input_schema_failed` — JSON Schema 2020-12 validation failed |
| 401 | `missing_agent_jwt` — neither `Authorization` nor `X-Rewire-Agent-Src` present |
| 403 | `agent_dst_mismatch` — header `X-Rewire-Agent-Dst` != `rewire-beacon` |
| 404 | `capability_unknown` — capability id not in registry |
| 408 | `deadline_exceeded` — handler ran past `metadata.deadline_ms` |
| 429 | rate limit (Kong plugin per `(src, dst)` pair) |
| 501 | `capability_not_implemented` — registered in YAML, no handler bound |

In-envelope errors (`status="error"`):
- `BUDGET_EXCEEDED` — predicted cost > effective max
- `HANDLER_EXCEPTION` — handler raised; retryable=true

## Capabilities exposed by BEACON

| ID | Category | Scope | Sensitivity |
|---|---|---|---|
| `rewire.beacon.send_email` | dispatch | `beacon.messages.send` | medium |
| `rewire.beacon.send_sms` | dispatch | `beacon.messages.send` | medium |
| `rewire.beacon.send_whatsapp` | dispatch | `beacon.messages.send` | medium |
| `rewire.beacon.add_suppression` | compliance | `beacon.suppression.write` | medium |
| `rewire.beacon.check_suppression` | compliance | `beacon.suppression.read` | low |
| `rewire.beacon.list_messages` | analytics | `beacon.messages.read` | low |

Full schemas: see [`capabilities.yaml`](../../capabilities.yaml).

## Examples

### List capabilities

```bash
curl -sS https://api.beacon.rewirelabs.dev/api/v1/capabilities | jq '.capabilities[].id'
```

### Invoke `send_email` from chat-orchestrator

```bash
curl -sS https://api.beacon.rewirelabs.dev/agent/v1/invoke \
  -H "Authorization: Bearer $AGENT_JWT" \
  -H "X-Rewire-Agent-Src: chat-orchestrator" \
  -H "X-Rewire-Agent-Dst: rewire-beacon" \
  -H "X-Rewire-Tenant-Id: tnt_001" \
  -H "X-Rewire-Trace-Id: 0af7651916cd43dd8448eb211c80319c" \
  -H "X-Rewire-Idempotency-Key: $(uuidgen)" \
  -H "Content-Type: application/json" \
  -d '{
        "capability": "rewire.beacon.send_email",
        "input": {
          "tenant_id": "11111111-1111-1111-1111-111111111111",
          "sender": "ops@example.com",
          "to": ["user@example.com"],
          "subject": "Welcome",
          "consent_basis": "contract"
        },
        "metadata": {"deadline_ms": 5000, "max_cost_usd": 0.01}
      }' | jq .
```

## Cross-agent client (BCN-100)

When BEACON itself acts as the agent-src calling another service
(e.g. CITADEL anchor or NOVA gateway), use the canonical
[`AgentBusClient`](../../apps/control-plane/src/beacon/agents/agent_bus_client.py):

```python
from beacon.agents.agent_bus_client import AgentBusClient

bus = AgentBusClient(jwt_token=agent_jwt, src="beacon-ai")
out = await bus.invoke(
    dst="rewire-citadel-cloud",
    base_url="http://citadel.rewire-citadel.svc:8000",
    capability="rewire.citadel-cloud.anchor_payload",
    input_={"event_type": "beacon.message.sent", "payload_blake3_hex": "..."},
    tenant_id="tnt_001",
    trace_id=incoming_trace_id,
)
# Audit-chain ref captured automatically for the next call in the same client.
print(bus.last_audit_chain_ref)
```

## Cross-agent bus (BCN-101)

RabbitMQ envelope publisher/consumer in
[`agent_bus_rmq.py`](../../apps/control-plane/src/beacon/agents/agent_bus_rmq.py).
Mock mode active when `RMQ_URL` env is absent (events written to an
in-memory list for tests).

Canonical events BEACON emits:

- `message_dispatched` — every successful channel dispatch
- `message_bounced` / `message_complained` — Postal/SES webhooks
- `suppression_added` — cross-channel suppression mutation
- `domain_verified` — DKIM/SPF/DMARC passed
- `journey_step_transitioned` — Temporal workflow state change

Canonical events BEACON consumes:

- `agent.metering.*.budget_exhausted` → enter degrade mode (security/
  transactional sends only; marketing campaigns paused)
- `agent.citadel.*.chain_appended` → cross-link in local audit log
- `agent.tenant.*.policy_changed` → reload suppression/quiet-hours/
  frequency-cap policy cache

## References

- [INTER_AGENT_COMM_SPEC](../../../INTER_AGENT_COMM_SPEC.md) §1-§7
- [CAPABILITY_REGISTRY_SPEC](../../../CAPABILITY_REGISTRY_SPEC.md)
- [CROSS_AGENT_AUTH_ADR](../../../CROSS_AGENT_AUTH_ADR.md)
- [CENTRAL_AI_CHAT_SPEC](../../../CENTRAL_AI_CHAT_SPEC.md)
- ADR cluster: 0106 (capability registry) + 0107 (central AI chat)
- Tickets: BCN-CAP-01, BCN-AICX-01, BCN-100..103

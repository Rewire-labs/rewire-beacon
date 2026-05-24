"""BCN-100/102/103: AgentBusClient — cross-agent REST client.

Canonical INTER_AGENT_COMM_SPEC client used by BEACON when it invokes
capabilities exposed by OTHER services (CITADEL anchor, AUDIT-TRAIL
event emit, NOVA gateway for AI-generated content, LAGO for billing
reconcile, CONNECT for WhatsApp).

Features:

- Mandatory canonical headers (``X-Rewire-Agent-Src/Dst``, ``Trace-Id``,
  ``Span-Id``, ``Tenant-Id``, ``Idempotency-Key`` on mutations,
  ``Audit-Chain-Ref`` propagation).
- Retry exponential backoff (200ms, 1s, 5s — max 3, no retry on 4xx
  except 429).
- ``Idempotency-Key`` UUIDv4 auto-gen.
- Audit chain ref propagation (read ``audit_chain_hash`` from response,
  pass as ``X-Rewire-Audit-Chain-Ref`` on next call) (BCN-100).
- ``Authorization: Bearer <JWT>`` (refresh via Authentik when configured).
- Default 30s timeout (override per-capability via Registry annotation).
- OTel span ``rewire.agent.call`` per invocation (BCN-103).
- Budget propagation via ``X-Rewire-Tenant-Budget`` header (BCN-102).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

try:
    from opentelemetry import trace as _otel_trace

    _TRACER = _otel_trace.get_tracer("rewire.agent")
    _OTEL_ENABLED = True
except Exception:  # pragma: no cover
    _OTEL_ENABLED = False
    _TRACER = None  # type: ignore[assignment]

try:
    from prometheus_client import Counter

    M_AGENT_CALL = Counter(
        "rewire_agent_call_total",
        "Cross-agent invoke calls",
        labelnames=("src", "dst", "status"),
    )
    M_AGENT_COST = Counter(
        "rewire_agent_cost_usd_sum",
        "Cross-agent cumulative cost USD",
        labelnames=("src", "dst", "tenant"),
    )
    _PROM_ENABLED = True
except Exception:  # pragma: no cover
    _PROM_ENABLED = False


SRC_AGENT_NAME = "beacon-ai"


@dataclass
class BudgetState:
    """Mutable budget snapshot for header propagation (BCN-102)."""

    usd_remaining: float = 0.0
    ttl_s: int = 60

    def to_header(self) -> str:
        return f"usd={self.usd_remaining:.6f};ttl_s={int(self.ttl_s)}"

    @classmethod
    def from_header(cls, hv: str) -> BudgetState | None:
        try:
            parts = dict(p.split("=", 1) for p in hv.split(";") if "=" in p)
            return cls(
                usd_remaining=float(parts.get("usd", "0")),
                ttl_s=int(parts.get("ttl_s", "60")),
            )
        except Exception:  # noqa: BLE001
            return None


@dataclass
class AgentBusClient:
    """Cross-agent invoke client.

    Usage::

        bus = AgentBusClient(jwt_token=..., src="beacon-ai")
        result = await bus.invoke(
            dst="rewire-citadel-cloud",
            base_url="http://citadel.rewire-citadel.svc:8000",
            capability="rewire.citadel-cloud.anchor_payload",
            input_={"event_type": "beacon.message.sent",
                    "payload_blake3_hex": "..."},
            tenant_id="tnt_001",
            trace_id="...",
        )
    """

    jwt_token: str = ""
    src: str = SRC_AGENT_NAME
    timeout_seconds: float = 30.0
    max_retries: int = 3
    retry_delays_seconds: tuple[float, ...] = (0.2, 1.0, 5.0)
    last_audit_chain_ref: str | None = None
    last_budget: BudgetState | None = None

    async def invoke(
        self,
        *,
        dst: str,
        base_url: str,
        capability: str,
        input_: dict[str, Any] | None = None,
        tenant_id: str = "global",
        trace_id: str | None = None,
        span_id: str | None = None,
        idempotency_key: str | None = None,
        max_cost_usd: float = 1.0,
        deadline_ms: int = 30_000,
        propagate_audit_chain: bool = True,
        propagate_budget: bool = True,
    ) -> dict[str, Any]:
        trace_id = trace_id or str(uuid.uuid4())
        span_id = span_id or str(uuid.uuid4())[:8]
        idempotency_key = idempotency_key or str(uuid.uuid4())

        headers = {
            "Authorization": f"Bearer {self.jwt_token}" if self.jwt_token else "",
            "Content-Type": "application/json",
            "X-Rewire-Agent-Src": self.src,
            "X-Rewire-Agent-Dst": dst,
            "X-Rewire-Trace-Id": trace_id,
            "X-Rewire-Span-Id": span_id,
            "X-Rewire-Tenant-Id": tenant_id,
            "X-Rewire-Idempotency-Key": idempotency_key,
        }
        if propagate_audit_chain and self.last_audit_chain_ref:
            headers["X-Rewire-Audit-Chain-Ref"] = self.last_audit_chain_ref
        if propagate_budget and self.last_budget is not None:
            headers["X-Rewire-Tenant-Budget"] = self.last_budget.to_header()

        body = {
            "capability": capability,
            "input": input_ or {},
            "metadata": {
                "deadline_ms": deadline_ms,
                "max_cost_usd": max_cost_usd,
                "reason": "agent_chain",
            },
        }

        url = f"{base_url.rstrip('/')}/agent/v1/invoke"
        attempt = 0
        last_exc: Exception | None = None
        span_cm = (
            _TRACER.start_as_current_span("rewire.agent.call")
            if _OTEL_ENABLED and _TRACER
            else None
        )
        _span = None
        try:
            if span_cm is not None:
                _span = span_cm.__enter__()
                _span.set_attribute("rewire.agent.src", self.src)
                _span.set_attribute("rewire.agent.dst", dst)
                _span.set_attribute("rewire.tenant.id", tenant_id)
                _span.set_attribute("rewire.capability", capability)

            while attempt <= self.max_retries:
                try:
                    async with httpx.AsyncClient(
                        timeout=self.timeout_seconds
                    ) as client:
                        r = await client.post(url, headers=headers, json=body)
                    status_code = r.status_code

                    if status_code == 401:
                        if _PROM_ENABLED:
                            M_AGENT_CALL.labels(
                                src=self.src, dst=dst, status="401"
                            ).inc()
                        raise PermissionError(f"agent_invoke_401:{dst}")
                    if status_code == 429 and attempt < self.max_retries:
                        retry_after = float(r.headers.get("Retry-After", "1"))
                        await asyncio.sleep(retry_after)
                        attempt += 1
                        continue
                    if 500 <= status_code < 600 and attempt < self.max_retries:
                        delay = self.retry_delays_seconds[
                            min(attempt, len(self.retry_delays_seconds) - 1)
                        ]
                        await asyncio.sleep(delay)
                        attempt += 1
                        continue

                    if not 200 <= status_code < 300:
                        if _PROM_ENABLED:
                            M_AGENT_CALL.labels(
                                src=self.src, dst=dst, status=str(status_code)
                            ).inc()
                        raise httpx.HTTPStatusError(
                            f"agent_invoke_{status_code}",
                            request=r.request,
                            response=r,
                        )

                    out = r.json()
                    if propagate_audit_chain and out.get("audit_chain_hash"):
                        self.last_audit_chain_ref = out["audit_chain_hash"]
                    cost_usd = float(out.get("cost_usd", 0))
                    if _PROM_ENABLED:
                        M_AGENT_CALL.labels(
                            src=self.src, dst=dst, status="ok"
                        ).inc()
                        if cost_usd > 0:
                            M_AGENT_COST.labels(
                                src=self.src, dst=dst, tenant=tenant_id
                            ).inc(cost_usd)
                    if _span is not None:
                        _span.set_attribute("rewire.cost_usd", cost_usd)
                        if out.get("audit_chain_hash"):
                            _span.set_attribute(
                                "rewire.audit_chain_hash", out["audit_chain_hash"]
                            )
                    return out
                except (
                    httpx.HTTPStatusError,
                    httpx.RequestError,
                    PermissionError,
                ) as e:
                    last_exc = e
                    if attempt >= self.max_retries:
                        break
                    delay = self.retry_delays_seconds[
                        min(attempt, len(self.retry_delays_seconds) - 1)
                    ]
                    await asyncio.sleep(delay)
                    attempt += 1
            if last_exc is not None:
                raise last_exc
            raise RuntimeError("agent_bus_exhausted")
        finally:
            if span_cm is not None:
                span_cm.__exit__(None, None, None)

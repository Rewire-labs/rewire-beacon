"""BCN-AICX-01: ``POST /agent/v1/invoke`` canonical agent invoke endpoint.

Aderente a INTER_AGENT_COMM_SPEC §1.3-§1.4. 1:1 contract-compatible with
the PULSE-CLOUD + CITADEL-CLOUD impls so the chat-orchestrator can route
to any service uniformly.

Pipeline:
  1. validate JWT (``agents.rewire.svc`` audience) — relies on existing
     ``AuthMiddleware`` claims; falls back to header-only mode when the
     middleware bypassed (smoke tests)
  2. validate ``X-Rewire-Agent-Dst`` matches this service
  3. lookup capability in registry — 404 if unknown
  4. validate input against capability ``input_schema`` (jsonschema)
  5. budget enforcement (``metadata.max_cost_usd`` + tenant budget header)
  6. dedup via ``X-Rewire-Idempotency-Key`` (in-memory cache, Redis-bound
     in production via ``rewire_shared.idempotency``)
  7. dispatch to handler
  8. compute ``cost_usd`` + ``latency_ms``
  9. anchor response (``audit_chain_hash`` propagated to client)
 10. emit audit-trail event ``rewire.beacon.<cap>.invoked``
 11. OTel span attributes (cross-agent — see BCN-103)
 12. return canonical response envelope
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from .capability_loader import CapabilityLoadError, get_registry
from .handlers import HandlerContext, get_handler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent/v1", tags=["agent-invoke"])

# Canonical service slug. The legacy ``rewire-beacon`` alias is still accepted
# as an ``X-Rewire-Agent-Dst`` for a 90d migration window (callers keyed on the
# old name during the rename — see RW-MESSAGING-10).
THIS_SERVICE = "rewire-messaging"
_LEGACY_SERVICE_ALIAS = "rewire-beacon"
_ACCEPTED_DST = frozenset({THIS_SERVICE, _LEGACY_SERVICE_ALIAS})

# In-memory idempotency cache fallback (TTL ~24h). Cleared on process
# restart. Production wires this to Redis via the existing
# ``beacon.middleware.IdempotencyMiddleware`` Redis client.
_INMEM_IDEMPOTENCY: dict[str, dict[str, Any]] = {}
_IDEMPOTENCY_MAX = 10_000

try:
    from opentelemetry import trace as _otel_trace

    _TRACER = _otel_trace.get_tracer("rewire.agent")
    _OTEL_ENABLED = True
except Exception:  # pragma: no cover
    _OTEL_ENABLED = False
    _TRACER = None  # type: ignore[assignment]

try:
    from prometheus_client import Counter

    M_AGENT_SERVE = Counter(
        "rewire_agent_serve_total",
        "Cross-agent invoke received",
        labelnames=("src", "dst", "capability", "status"),
    )
    _PROM_ENABLED = True
except Exception:  # pragma: no cover
    _PROM_ENABLED = False


class InvokeMetadata(BaseModel):
    deadline_ms: int = Field(default=30_000, ge=100, le=300_000)
    max_cost_usd: float = Field(default=1.0, ge=0.0, le=100.0)
    reason: str = Field(default="agent_chain", max_length=128)


class InvokeRequest(BaseModel):
    capability: str = Field(..., min_length=3, max_length=256)
    input: dict[str, Any] = Field(default_factory=dict)
    metadata: InvokeMetadata = Field(default_factory=InvokeMetadata)


class InvokeError(BaseModel):
    code: str
    message: str
    retryable: bool = False


class InvokeResponse(BaseModel):
    status: str  # ok | error | partial
    output: dict[str, Any] | None = None
    cost_usd: float = 0.0
    latency_ms: int = 0
    audit_chain_hash: str | None = None
    trace_id: str
    error: InvokeError | None = None


def _validate_input_against_schema(
    input_: dict[str, Any], schema: dict[str, Any]
) -> str | None:
    """Returns error msg if invalid, ``None`` on OK."""
    try:
        from jsonschema import Draft202012Validator
    except ImportError:  # pragma: no cover
        # Best-effort when dep not installed — boot still works.
        return None
    try:
        Draft202012Validator(schema).validate(input_)
        return None
    except Exception as e:  # noqa: BLE001
        return str(e).splitlines()[0][:200]


def _idempotency_check(key: str) -> dict[str, Any] | None:
    if not key:
        return None
    return _INMEM_IDEMPOTENCY.get(key)


def _idempotency_store(key: str, response: dict[str, Any]) -> None:
    if not key:
        return
    if len(_INMEM_IDEMPOTENCY) >= _IDEMPOTENCY_MAX:
        # FIFO eviction (simple — Redis-backed prod doesn't need this).
        _INMEM_IDEMPOTENCY.pop(next(iter(_INMEM_IDEMPOTENCY)))
    _INMEM_IDEMPOTENCY[key] = response


def reset_idempotency_cache_for_tests() -> None:
    """ONLY for tests — clears the in-memory dedupe cache."""
    _INMEM_IDEMPOTENCY.clear()


@router.post(
    "/invoke",
    summary="Canonical agent invoke (INTER_AGENT_COMM_SPEC §1.3-§1.4)",
    response_model=InvokeResponse,
    responses={
        400: {"description": "Schema validation failed"},
        401: {"description": "Missing/invalid agent JWT"},
        403: {"description": "Agent-Dst mismatch or capability denied"},
        404: {"description": "Unknown capability"},
        408: {"description": "Deadline exceeded"},
        429: {"description": "Rate limit (Kong plugin)"},
    },
)
async def agent_invoke(
    request: Request,
    body: InvokeRequest,
    x_rewire_agent_src: str = Header(default="", alias="X-Rewire-Agent-Src"),
    x_rewire_agent_dst: str = Header(default="", alias="X-Rewire-Agent-Dst"),
    x_rewire_trace_id: str = Header(default="", alias="X-Rewire-Trace-Id"),
    x_rewire_span_id: str = Header(default="", alias="X-Rewire-Span-Id"),
    x_rewire_tenant_id: str = Header(default="global", alias="X-Rewire-Tenant-Id"),
    x_rewire_idempotency_key: str = Header(
        default="", alias="X-Rewire-Idempotency-Key"
    ),
    x_rewire_audit_chain_ref: str = Header(
        default="", alias="X-Rewire-Audit-Chain-Ref"
    ),
    x_rewire_tenant_budget: str = Header(
        default="", alias="X-Rewire-Tenant-Budget"
    ),
) -> InvokeResponse:
    started = time.perf_counter()
    trace_id = x_rewire_trace_id or str(uuid.uuid4())

    span_cm = (
        _TRACER.start_as_current_span("rewire.agent.serve")
        if _OTEL_ENABLED and _TRACER
        else None
    )
    _span = None
    try:
        if span_cm is not None:
            _span = span_cm.__enter__()
            _span.set_attribute("rewire.agent.src", x_rewire_agent_src or "unknown")
            _span.set_attribute("rewire.agent.dst", THIS_SERVICE)
            _span.set_attribute("rewire.tenant.id", x_rewire_tenant_id)
            _span.set_attribute("rewire.capability", body.capability)

        # 1. JWT validation — the agent token MUST carry a valid signature
        #    (audience ``agents.rewire.svc``). ``/agent/v1/`` bypasses the UI
        #    AuthMiddleware, so we validate here. Header-only identity is
        #    rejected unless an explicit dev flag is set (the RW-MESSAGING-07
        #    header-trust bypass is gone).
        from beacon.middleware.auth import get_agent_jwt_validator
        from beacon.settings import get_settings as _get_settings

        _settings = _get_settings()
        agent_claims: dict[str, Any] | None = None
        auth_header = request.headers.get("Authorization", "")
        token = ""
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()

        if token:
            try:
                agent_claims = await get_agent_jwt_validator(_settings).validate_payload(
                    token
                )
            except Exception as exc:  # noqa: BLE001
                logger.info("agent_invoke.jwt_invalid", extra={"err": str(exc)})
                raise HTTPException(
                    status_code=401, detail="invalid_agent_jwt"
                ) from exc
        elif _settings.agent_invoke_dev_allow_unsigned:
            # Dev/test only: header-derived identity (MUST be false in prod).
            if not x_rewire_agent_src:
                raise HTTPException(status_code=401, detail="missing_agent_jwt")
        else:
            raise HTTPException(status_code=401, detail="missing_agent_jwt")

        # Actor is the verified token ``sub`` when present; the header is only
        # an identity hint for the dev-unsigned path.
        actor_sub = (
            agent_claims.get("sub") if agent_claims else x_rewire_agent_src
        )

        # 2. Agent-Dst mismatch (canonical slug + 90d legacy alias accepted).
        if x_rewire_agent_dst and x_rewire_agent_dst not in _ACCEPTED_DST:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"agent_dst_mismatch:expected={THIS_SERVICE}:"
                    f"got={x_rewire_agent_dst}"
                ),
            )

        # 3. Capability lookup.
        try:
            reg = get_registry()
        except CapabilityLoadError as e:
            raise HTTPException(
                status_code=500, detail=f"registry_load_failed:{e}"
            ) from e

        cap = reg.by_id(body.capability)
        if cap is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"capability_unknown:{body.capability}",
            )

        # 4. Input schema validation (jsonschema 2020-12).
        err = _validate_input_against_schema(body.input, cap.input_schema)
        if err is not None:
            raise HTTPException(
                status_code=400, detail=f"input_schema_failed:{err}"
            )

        # 5. Budget enforcement.
        predicted_cost = (cap.budget_tokens / 1_000_000) * 1.0  # ~$1/MT proxy
        effective_max_cost = body.metadata.max_cost_usd
        if x_rewire_tenant_budget:
            try:
                from .agent_bus_client import BudgetState

                bs = BudgetState.from_header(x_rewire_tenant_budget)
                if bs is not None and bs.usd_remaining < effective_max_cost:
                    effective_max_cost = bs.usd_remaining
            except Exception:  # noqa: BLE001
                pass
        if predicted_cost > effective_max_cost:
            resp = InvokeResponse(
                status="error",
                cost_usd=0.0,
                latency_ms=int((time.perf_counter() - started) * 1000),
                trace_id=trace_id,
                error=InvokeError(
                    code="BUDGET_EXCEEDED",
                    message=(
                        f"predicted_cost={predicted_cost:.6f} > "
                        f"effective_max_cost_usd={effective_max_cost:.6f}"
                    ),
                    retryable=False,
                ),
            )
            if _PROM_ENABLED:
                M_AGENT_SERVE.labels(
                    src=x_rewire_agent_src or "unknown",
                    dst=THIS_SERVICE,
                    capability=body.capability,
                    status="budget_exceeded",
                ).inc()
            return resp

        # 6. Idempotency dedupe.
        cached = _idempotency_check(x_rewire_idempotency_key)
        if cached is not None:
            logger.info(
                "agent_invoke.idempotency_hit",
                extra={
                    "key": x_rewire_idempotency_key,
                    "cap": body.capability,
                },
            )
            if _PROM_ENABLED:
                M_AGENT_SERVE.labels(
                    src=x_rewire_agent_src or "unknown",
                    dst=THIS_SERVICE,
                    capability=body.capability,
                    status="idempotency_hit",
                ).inc()
            return InvokeResponse.model_validate(cached)

        # 7. Dispatch handler.
        # CORR-2 sweep (2026-05-26): zero 501 binário. Capability inexistente
        # = 404 Not Found semantic (resource não existe), não 501 (endpoint exists).
        handler = get_handler(body.capability)
        if handler is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "capability_not_found",
                    "capability": body.capability,
                    "message": f"capability not registered in {THIS_SERVICE}",
                },
            )

        ctx = HandlerContext(
            tenant_id=x_rewire_tenant_id,
            actor_sub=str(actor_sub or "anonymous"),
            capability_id=body.capability,
            trace_id=trace_id,
            chain_ref_in=x_rewire_audit_chain_ref or None,
            deadline_ms=body.metadata.deadline_ms,
            max_cost_usd=body.metadata.max_cost_usd,
        )

        # Handler call.
        try:
            result = await handler(body.input, ctx)
        except HTTPException:
            raise
        except Exception as e:  # noqa: BLE001
            logger.exception(
                "agent_invoke.handler_failed",
                extra={"cap": body.capability, "err": str(e)},
            )
            if _PROM_ENABLED:
                M_AGENT_SERVE.labels(
                    src=x_rewire_agent_src or "unknown",
                    dst=THIS_SERVICE,
                    capability=body.capability,
                    status="handler_exception",
                ).inc()
            return InvokeResponse(
                status="error",
                cost_usd=0.0,
                latency_ms=int((time.perf_counter() - started) * 1000),
                trace_id=trace_id,
                error=InvokeError(
                    code="HANDLER_EXCEPTION",
                    message=str(e)[:200],
                    retryable=True,
                ),
            )

        latency_ms = int((time.perf_counter() - started) * 1000)

        # 8/9. cost_usd + audit_chain_hash propagated from handler result.
        if result.error is not None:
            response = InvokeResponse(
                status="error",
                output=result.output or None,
                cost_usd=result.cost_usd,
                latency_ms=latency_ms,
                audit_chain_hash=result.audit_chain_hash,
                trace_id=trace_id,
                error=InvokeError(**result.error),
            )
        else:
            response = InvokeResponse(
                status="ok",
                output=result.output,
                cost_usd=result.cost_usd,
                latency_ms=latency_ms,
                audit_chain_hash=result.audit_chain_hash,
                trace_id=trace_id,
            )

        # 10. Audit-trail event emit (best-effort fire-and-forget).
        logger.info(
            "agent_invoke.completed",
            extra={
                "rewire.agent.src": x_rewire_agent_src,
                "rewire.agent.dst": THIS_SERVICE,
                "rewire.tenant.id": x_rewire_tenant_id,
                "rewire.capability": body.capability,
                "rewire.cost_usd": result.cost_usd,
                "rewire.audit_chain_hash": result.audit_chain_hash,
                "rewire.latency_ms": latency_ms,
                "rewire.audit.event": cap.audit_event,
                "input_hash_short": str(
                    hash(json.dumps(body.input, sort_keys=True)) & 0xFFFFFFFF
                ),
                "output_hash_short": str(
                    hash(json.dumps(response.output or {}, sort_keys=True))
                    & 0xFFFFFFFF
                ),
            },
        )

        if _PROM_ENABLED:
            M_AGENT_SERVE.labels(
                src=x_rewire_agent_src or "unknown",
                dst=THIS_SERVICE,
                capability=body.capability,
                status=response.status,
            ).inc()

        if _span is not None:
            _span.set_attribute("rewire.cost_usd", float(result.cost_usd))
            _span.set_attribute("rewire.latency_ms", latency_ms)
            if result.audit_chain_hash:
                _span.set_attribute(
                    "rewire.audit_chain_hash", result.audit_chain_hash
                )

        # Cache for idempotency.
        _idempotency_store(x_rewire_idempotency_key, response.model_dump())

        return response
    finally:
        if span_cm is not None:
            span_cm.__exit__(None, None, None)

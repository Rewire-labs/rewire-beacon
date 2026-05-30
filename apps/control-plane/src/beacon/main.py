"""BEACON control-plane FastAPI entrypoint (V0 skeleton).

Functional endpoints:
- GET  /healthz  -> 200 {"status":"ok"}
- GET  /ready    -> 200 {"status":"ready"}
- GET  /metrics  -> Prometheus exposition format
- GET  /openapi.json (FastAPI default)

Business endpoints are stubs returning {"status":"not_implemented","todo":"V0.2"}.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from beacon.api import router as api_router
from beacon.middleware import AuthMiddleware, IdempotencyMiddleware, TenancyMiddleware
from beacon.settings import get_settings

logger = structlog.get_logger(__name__)


def _configure_logging(level: str) -> None:
    """Structlog + stdlib bridge — canonical Rewire pattern."""
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


async def _aggregator_invalidate(logger_: structlog.stdlib.BoundLogger) -> None:
    """BCN-CAP-01: fire-and-forget aggregator invalidate webhook.

    Tells the central rewire-mcp aggregator to re-pull the capability
    registry so the chat-orchestrator sees the fresh contract after
    a deploy. URL via env ``REWIRE_AGGREGATOR_URL``. No-op if unset.
    """
    import os as _os

    base = (_os.environ.get("REWIRE_AGGREGATOR_URL", "") or "").rstrip("/")
    if not base:
        return
    try:
        import httpx as _httpx

        async with _httpx.AsyncClient(timeout=2.0) as ac:
            await ac.post(
                f"{base}/aggregator/invalidate",
                # RW-MESSAGING-10: canonical slug is rewire-messaging.
                # Legacy rewire-beacon accepted by aggregator for 90d alias window.
                json={"service": "rewire-messaging", "reason": "deploy"},
            )
        logger_.info("capability_registry.aggregator_invalidated")
    except Exception as exc:  # noqa: BLE001
        logger_.warning(
            "capability_registry.aggregator_invalidate.failed", error=str(exc)
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown lifecycle — V0 minimal (sem DB connect, sem workers)."""
    s = get_settings()
    _configure_logging(s.log_level)
    logger.info(
        "beacon.startup",
        service=s.service_name,
        version=s.service_version,
        environment=s.environment,
    )
    app.state.settings = s
    # BCN-CAP-01: lazy-load capability registry to fail fast on malformed
    # YAML at boot (not on first request).
    try:
        from beacon.agents.capability_loader import get_registry

        _reg = get_registry()
        logger.info(
            "beacon.capability_registry.loaded",
            count=len(_reg.capabilities),
            etag=_reg.etag,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("beacon.capability_registry.load_failed", error=str(exc))
    # BCN-CAP-01: ping aggregator post-start (fire-and-forget).
    await _aggregator_invalidate(logger)
    try:
        yield
    finally:
        logger.info("beacon.shutdown", service=s.service_name)


def _wire_otel(app: FastAPI, service_name: str, otlp_endpoint: str) -> None:
    """RW-MESSAGING-15: wire FastAPI + OTLP trace exporter.

    Instruments the app so every request produces a span in Tempo/Jaeger.
    No-op if the opentelemetry-instrumentation-fastapi package is absent
    (dev environments without observability stack).
    """
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": service_name, "product": "messaging"})
        provider = TracerProvider(resource=resource)
        if otlp_endpoint:
            exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        logger.info("otel.fastapi.instrumented", service=service_name, otlp_endpoint=otlp_endpoint)
    except Exception as exc:  # noqa: BLE001
        logger.warning("otel.fastapi.instrument_failed", error=str(exc))


def create_app() -> FastAPI:
    """FastAPI factory — used by uvicorn and tests."""
    s = get_settings()
    app = FastAPI(
        # RW-MESSAGING-10: canonical title is rewire-messaging.
        title="rewire-messaging",
        description="Rewire MESSAGING — Notification platform multi-canal BR (V0)",
        version=s.service_version,
        lifespan=lifespan,
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # RW-MESSAGING-15: wire OTel FastAPI instrumentation + OTLP exporter.
    _wire_otel(app, s.otel_service_name, s.otel_exporter_otlp_endpoint)

    @app.get("/healthz", tags=["health"], include_in_schema=True)
    async def healthz() -> JSONResponse:
        return JSONResponse(
            {"status": "ok", "service": s.service_name, "version": s.service_version}
        )

    @app.get("/ready", tags=["health"], include_in_schema=True)
    async def ready() -> JSONResponse:
        # RW-MESSAGING-13: real readiness — DB + Redis bounded checks (≤2s).
        # Returns 503 when any critical dependency is unreachable so K8s
        # withholds traffic until the pod is genuinely healthy.
        checks: dict[str, str] = {}
        failed = False

        # Postgres check
        try:
            from beacon.db.session import get_engine
            from sqlalchemy import text as _text
            engine = get_engine()
            async with engine.connect() as conn:
                await conn.execute(_text("SELECT 1"))
            checks["postgres"] = "ok"
        except Exception as exc:  # noqa: BLE001
            checks["postgres"] = f"error: {exc}"
            failed = True

        # Redis check
        try:
            import redis.asyncio as _aioredis
            _redis = _aioredis.from_url(s.redis_url, socket_connect_timeout=2)
            await _redis.ping()
            await _redis.aclose()
            checks["redis"] = "ok"
        except Exception as exc:  # noqa: BLE001
            checks["redis"] = f"error: {exc}"
            failed = True

        if failed:
            return JSONResponse(
                {"status": "not_ready", "service": s.service_name, "checks": checks},
                status_code=503,
            )
        return JSONResponse(
            {"status": "ready", "service": s.service_name, "checks": checks}
        )

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> PlainTextResponse:
        return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    # Middleware order: outer-most added LAST. Wanted execution order on
    # request: RED -> Auth -> Tenancy -> Idempotency -> handler.
    # CORR-2 sweep (2026-05-26): RED middleware canonical para emit HTTP_REQUESTS_TOTAL
    # + HTTP_REQUEST_DURATION_SECONDS auto-wired em cada request.
    app.add_middleware(IdempotencyMiddleware)
    app.add_middleware(TenancyMiddleware)
    app.add_middleware(AuthMiddleware)
    try:
        from .red_middleware import REDMiddleware
        app.add_middleware(REDMiddleware)
    except Exception:  # noqa: BLE001
        pass

    app.include_router(api_router, prefix="/v1")

    # MSG-V0 (Slot 4 Run 4): canonical /v1 surface (messaging_cp.api). Co-exists
    # with legacy beacon.api routers above — same prefix, distinct routes.
    # New consumers (rewire-app, rewire-admin) import via messaging_cp.* path.
    try:
        from messaging_cp.api import router as _msg_v1_router  # noqa: WPS433

        app.include_router(_msg_v1_router)
        logger.info("messaging.canonical_v1.mounted")
    except Exception as exc:  # noqa: BLE001
        logger.warning("messaging.canonical_v1.mount_failed", error=str(exc))

    # BCN-CAP-01 + BCN-AICX-01 — canonical agent registry + invoke endpoints.
    # Lazy import so legacy tests/installer flows don't pay the YAML-load cost
    # at import time.
    from beacon.agents.agent_invoke_router import router as _agent_invoke_router
    from beacon.agents.capabilities_router import router as _capabilities_router

    app.include_router(_capabilities_router)     # GET /api/v1/capabilities
    app.include_router(_agent_invoke_router)     # POST /agent/v1/invoke

    # GAP-CLOSURE 2 (2026-05-25) — AUDIT-orchestrator-facing /internal/v1/dsar/*
    try:
        from beacon.api.internal_dsar import router as _internal_dsar_router

        app.include_router(_internal_dsar_router, prefix="/internal/v1/dsar")
    except Exception as exc:  # noqa: BLE001
        logger.warning("internal_dsar.router_wire_failed", error=str(exc))

    return app


app = create_app()


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    s = get_settings()
    uvicorn.run(
        "beacon.main:app",
        host=s.http_host,
        port=s.http_port,
        log_level=s.log_level.lower(),
    )

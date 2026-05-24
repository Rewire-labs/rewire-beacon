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
                json={"service": "rewire-beacon", "reason": "deploy"},
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


def create_app() -> FastAPI:
    """FastAPI factory — used by uvicorn and tests."""
    s = get_settings()
    app = FastAPI(
        title="rewire-beacon",
        description="Rewire BEACON — Notification platform multi-canal BR (V0 skeleton)",
        version=s.service_version,
        lifespan=lifespan,
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    @app.get("/healthz", tags=["health"], include_in_schema=True)
    async def healthz() -> JSONResponse:
        return JSONResponse(
            {"status": "ok", "service": s.service_name, "version": s.service_version}
        )

    @app.get("/ready", tags=["health"], include_in_schema=True)
    async def ready() -> JSONResponse:
        # V0: nao temos DB/Redis/Kafka connect — ready = healthz.
        # V0.2: validar Postgres pool + Redis ping + Kafka producer.
        return JSONResponse({"status": "ready", "service": s.service_name})

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> PlainTextResponse:
        return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    # Middleware order: outer-most added LAST. Wanted execution order on
    # request: Auth -> Tenancy -> Idempotency -> handler.
    app.add_middleware(IdempotencyMiddleware)
    app.add_middleware(TenancyMiddleware)
    app.add_middleware(AuthMiddleware)

    app.include_router(api_router, prefix="/v1")

    # BCN-CAP-01 + BCN-AICX-01 — canonical agent registry + invoke endpoints.
    # Lazy import so legacy tests/installer flows don't pay the YAML-load cost
    # at import time.
    from beacon.agents.agent_invoke_router import router as _agent_invoke_router
    from beacon.agents.capabilities_router import router as _capabilities_router

    app.include_router(_capabilities_router)     # GET /api/v1/capabilities
    app.include_router(_agent_invoke_router)     # POST /agent/v1/invoke

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

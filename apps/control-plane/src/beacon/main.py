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

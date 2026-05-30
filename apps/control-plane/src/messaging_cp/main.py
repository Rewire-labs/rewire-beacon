# messaging control-plane main
"""FastAPI application factory for the Beacon control-plane.

Mounts the aggregated API router (FE-MESSAGING-07) under /v1 plus a health
probe. Kept import-light so it can be created in tests without external deps.
"""

from __future__ import annotations

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Beacon Control Plane", version="0.1.0")

    from beacon.api import api_router

    app.include_router(api_router, prefix="/v1")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()

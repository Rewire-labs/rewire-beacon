"""BEACON HTTP API routers (V0 stubs)."""

from __future__ import annotations

from fastapi import APIRouter

from beacon.api import api_tokens, deliveries, notifications, templates, webhooks

router = APIRouter()
router.include_router(notifications.router, tags=["notifications"])
router.include_router(templates.router, tags=["templates"])
router.include_router(deliveries.router, tags=["deliveries"])
router.include_router(webhooks.router, tags=["webhooks"])
router.include_router(api_tokens.router)

__all__ = ["router"]

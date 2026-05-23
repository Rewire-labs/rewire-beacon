"""BEACON HTTP API routers (V0 stubs)."""

from __future__ import annotations

from fastapi import APIRouter

from beacon.api import (
    api_tokens,
    deliveries,
    domains,
    messages,
    notifications,
    push_apps,
    suppression,
    templates,
    unsubscribe,
    webhooks,
    webhooks_inbound,
)

router = APIRouter()
router.include_router(notifications.router, tags=["notifications"])
router.include_router(templates.router, tags=["templates"])
router.include_router(deliveries.router, tags=["deliveries"])
router.include_router(webhooks.router, tags=["webhooks"])
router.include_router(api_tokens.router)
router.include_router(messages.router)
router.include_router(domains.router)
router.include_router(suppression.router)
router.include_router(unsubscribe.router)
router.include_router(webhooks_inbound.router)
router.include_router(push_apps.router)

__all__ = ["router"]

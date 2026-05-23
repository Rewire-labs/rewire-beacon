"""BEACON HTTP API routers (V0 stubs)."""

from __future__ import annotations

from fastapi import APIRouter

from beacon.api import (
    analytics,
    antispam,
    api_tokens,
    deliveries,
    domains,
    journeys,
    messages,
    notifications,
    push_apps,
    suppression,
    templates,
    unsubscribe,
    webhooks,
    webhooks_inbound,
    webpush_subs,
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
router.include_router(webpush_subs.router)
router.include_router(analytics.router)
router.include_router(journeys.router)
router.include_router(antispam.router)

__all__ = ["router"]

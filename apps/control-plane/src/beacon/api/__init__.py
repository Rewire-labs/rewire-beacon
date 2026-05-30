# beacon api package
"""Aggregates the FastAPI routers for the Beacon control-plane.

FE-MESSAGING-07 added the 6 previously FE-invented endpoints
(overview / sms-numbers / deliverability / chain / team / settings) so the
beacon-ui pages hit a real backend contract instead of silent 404s.
"""

from __future__ import annotations

from fastapi import APIRouter

from . import (
    ab_tests,
    analytics,
    antispam,
    api_tokens,
    billing,
    chain,
    deliverability,
    domains,
    journeys,
    lgpd,
    messages,
    notifications,
    overview,
    push_apps,
    segments,
    settings,
    sms_numbers,
    suppression,
    team,
    templates,
    webhooks,
    webhooks_mgmt,
    whatsapp,
)

# Single aggregated router mounted by the app under /v1.
# FE-MESSAGING-07: previously missing routers added; FE-MESSAGING-08: whatsapp router added.
api_router = APIRouter()
api_router.include_router(overview.router)
api_router.include_router(analytics.router)
api_router.include_router(sms_numbers.router)
api_router.include_router(deliverability.router)
api_router.include_router(chain.router)
api_router.include_router(team.router)
api_router.include_router(settings.router)
api_router.include_router(notifications.router)
api_router.include_router(antispam.router)
api_router.include_router(ab_tests.router)
api_router.include_router(api_tokens.router)
api_router.include_router(billing.router)
api_router.include_router(domains.router)
api_router.include_router(journeys.router)
api_router.include_router(lgpd.router)
api_router.include_router(messages.router)
api_router.include_router(push_apps.router)
api_router.include_router(segments.router)
api_router.include_router(suppression.router)
api_router.include_router(templates.router)
api_router.include_router(webhooks.router)
api_router.include_router(webhooks_mgmt.router)
api_router.include_router(whatsapp.router)

__all__ = ["api_router"]

# beacon api package
"""Aggregates the FastAPI routers for the Beacon control-plane.

FE-MESSAGING-07 added the 6 previously FE-invented endpoints
(overview / sms-numbers / deliverability / chain / team / settings) so the
beacon-ui pages hit a real backend contract instead of silent 404s.
"""

from __future__ import annotations

from fastapi import APIRouter

from . import (
    chain,
    deliverability,
    notifications,
    overview,
    settings,
    sms_numbers,
    team,
)

# Single aggregated router mounted by the app under /v1.
api_router = APIRouter()
api_router.include_router(overview.router)
api_router.include_router(sms_numbers.router)
api_router.include_router(deliverability.router)
api_router.include_router(chain.router)
api_router.include_router(team.router)
api_router.include_router(settings.router)
api_router.include_router(notifications.router)

__all__ = ["api_router"]

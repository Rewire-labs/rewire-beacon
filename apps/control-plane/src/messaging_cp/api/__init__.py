"""Canonical /v1 API surface for rewire-messaging (V0).

Routers:
  - emails.py    — POST /v1/emails  + GET /v1/emails/{id}
  - sms.py       — POST /v1/sms     + GET /v1/sms/{id}
  - push.py      — POST /v1/push    + POST /v1/push/devices
  - webhooks.py  — POST /v1/webhooks/{provider}
  - templates.py — CRUD templates per tenant

These re-export the legacy ``beacon.api.*`` routers under the canonical
``messaging_cp.api.v1`` namespace so consumers (rewire-app, rewire-admin)
can import the modern path without refactoring backend code.
"""

from __future__ import annotations

from fastapi import APIRouter

from messaging_cp.api.v1 import emails, push, sms, templates, webhooks

router = APIRouter()
router.include_router(emails.router, tags=["emails"])
router.include_router(sms.router, tags=["sms"])
router.include_router(push.router, tags=["push"])
router.include_router(webhooks.router, tags=["webhooks"])
router.include_router(templates.router, tags=["templates"])

__all__ = ["router"]

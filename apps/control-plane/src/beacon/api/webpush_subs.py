"""Web push subscription management endpoints.

- POST /v1/webpush/subscriptions      — register a browser subscription
- DELETE /v1/webpush/subscriptions/{id}
- GET  /v1/webpush/vapid-public-key   — returns public key for SW registration
- GET  /v1/webpush/sw.js              — server-rendered Service Worker JS

Subscriptions are stored as suppression list reverse: identifier_type=
`push_token` value = JSON-serialized subscription. We use a dedicated table
later if volume justifies; for V0 keep it lean.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from beacon.db.models import PushApp
from beacon.db.session import tenant_scoped_session
from beacon.services.vapid import generate_vapid_keypair

router = APIRouter(prefix="/webpush", tags=["webpush"])


class WebPushSubscription(BaseModel):
    endpoint: str
    keys: dict[str, str]
    expiration_time: int | None = None
    user_identifier: str | None = Field(None, description="Optional internal user id")


class WebPushSubOut(BaseModel):
    id: str
    endpoint: str
    created_at: datetime


def _require_org(request: Request) -> str:
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_required")
    return org_id


@router.get("/vapid-public-key")
async def vapid_public_key(request: Request) -> dict[str, str]:
    org_id = _require_org(request)
    async with tenant_scoped_session(org_id) as session:
        rows = list((await session.execute(
            select(PushApp).where(PushApp.organization_id == org_id, PushApp.platform == "web")
        )).scalars().all())
    if rows and rows[0].vapid_public_key:
        return {"public_key": rows[0].vapid_public_key}
    # Generate on demand (first call).
    pub, _priv = generate_vapid_keypair()
    async with tenant_scoped_session(org_id) as session:
        app = PushApp(
            organization_id=org_id, name="web-default", platform="web",
            vapid_public_key=pub,
            vapid_private_key_vault_path=f"vault/beacon/{org_id}/vapid_private",
        )
        session.add(app)
        await session.commit()
    return {"public_key": pub}


@router.post("/subscriptions", status_code=status.HTTP_201_CREATED, response_model=WebPushSubOut)
async def create_subscription(payload: WebPushSubscription, request: Request) -> WebPushSubOut:
    org_id = _require_org(request)
    # For V0 we keep the subscription JSON serialized in beacon.notifications.payload-style
    # via a lightweight dedicated approach: insert into webhooks.endpoints surrogate.
    # Proper webpush_subscriptions table is a later schema bump.
    import uuid as _uuid

    sub_id = str(_uuid.uuid4())
    # Store opaque blob in suppression with a special identifier_type prefix so we can list.
    from sqlalchemy import text as sql_text

    async with tenant_scoped_session(org_id) as session:
        await session.execute(sql_text(
            "INSERT INTO beacon.notifications (id, tenant_id, channel_kind, recipient, payload, created_at) "
            "VALUES (:id, :org, 'push_web_sub', :ep, :pl, now())"
        ).bindparams(id=sub_id, org=org_id, ep=payload.endpoint, pl=json.dumps(payload.dict())))
        await session.commit()
    return WebPushSubOut(id=sub_id, endpoint=payload.endpoint, created_at=datetime.utcnow())


@router.delete("/subscriptions/{sub_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(sub_id: str, request: Request) -> None:
    org_id = _require_org(request)
    from sqlalchemy import text as sql_text

    async with tenant_scoped_session(org_id) as session:
        await session.execute(sql_text(
            "DELETE FROM beacon.notifications WHERE id = :id AND tenant_id = :org AND channel_kind = 'push_web_sub'"
        ).bindparams(id=sub_id, org=org_id))
        await session.commit()


@router.get("/sw.js", response_class=PlainTextResponse)
async def service_worker_js(request: Request) -> PlainTextResponse:
    """Returns a generic Service Worker for web push.

    Hosted at api.beacon.rewirelabs.dev/v1/webpush/sw.js; customer page
    embeds <script>navigator.serviceWorker.register('/sw.js')</script>.
    """
    js = """// beacon-webpush v0.1 — Service Worker
self.addEventListener('push', function(event) {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch(e) {}
  const title = data.title || 'Notification';
  const options = {
    body: data.body || '',
    icon: data.icon || '/favicon.ico',
    data: data.data || {},
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  const url = event.notification.data && event.notification.data.url;
  if (url) event.waitUntil(clients.openWindow(url));
});
"""
    return PlainTextResponse(js, media_type="application/javascript")

"""Public unsubscribe portal `/v1/u/{token}` — LGPD Art. 18 cross-canal opt-out.

Token format: base64(org_id|identifier_type|identifier_value|hmac).
HMAC keyed with `BEACON_UNSUBSCRIBE_SECRET` (defaults to dev placeholder).

Flow:
- GET /v1/u/{token}        → render simple HTML showing channels opted-in
- POST /v1/u/{token}/all   → add suppression entries for all channels
- POST /v1/u/{token}/one   → add suppression entry for body.channel only
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from beacon.db.session import worker_session
from beacon.services import suppression as svc

router = APIRouter(prefix="/u", tags=["unsubscribe-public"], include_in_schema=False)


def _secret() -> bytes:
    return os.environ.get("BEACON_UNSUBSCRIBE_SECRET", "dev-unsub-secret-replace-in-prod").encode()


def generate_unsubscribe_token(*, organization_id: str, identifier_type: str, identifier_value: str) -> str:
    payload = f"{organization_id}|{identifier_type}|{identifier_value}"
    sig = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()[:16]
    return base64.urlsafe_b64encode(f"{payload}|{sig}".encode()).decode().rstrip("=")


def _decode_token(token: str) -> tuple[str, str, str]:
    try:
        raw = base64.urlsafe_b64decode(token + "==").decode()
        org_id, it, val, sig = raw.rsplit("|", 3)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_token")
    expected = hmac.new(_secret(), f"{org_id}|{it}|{val}".encode(), hashlib.sha256).hexdigest()[:16]
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=400, detail="invalid_token_signature")
    return org_id, it, val


@router.get("/{token}", response_class=HTMLResponse)
async def show_unsubscribe(token: str) -> HTMLResponse:
    org_id, it, val = _decode_token(token)
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Cancelar comunicacoes</title>
<style>body{{font-family:system-ui;padding:2rem;max-width:600px;margin:auto}}
button{{padding:.8rem 1.4rem;margin:.4rem;border:none;border-radius:6px;cursor:pointer;font-size:1rem}}
.btn-primary{{background:#d33;color:white}}.btn-secondary{{background:#666;color:white}}</style>
</head><body>
<h1>Cancelar comunicacoes</h1>
<p>Identificador: <code>{val}</code></p>
<p>Voce pode optar por nao receber mais mensagens desta empresa via BEACON.</p>
<form method="post" action="/v1/u/{token}/all">
  <button class="btn-primary" type="submit">Cancelar TODOS os canais</button>
</form>
<p style="color:#888;font-size:.85rem;margin-top:2rem">
LGPD Art. 18 - Direito a oposicao. Confirmacao instantanea.
</p>
</body></html>"""
    return HTMLResponse(html)


class UnsubChannelBody(BaseModel):
    channel: Literal["email", "sms", "whatsapp", "push_mobile", "push_web"]


@router.post("/{token}/all", response_class=HTMLResponse)
async def unsubscribe_all(token: str) -> HTMLResponse:
    org_id, it, val = _decode_token(token)
    async with worker_session() as session:
        await svc.add(
            session,
            organization_id=org_id,
            identifier_type=it,
            identifier_value=val,
            reason="unsubscribe",
            source_channel="all",
        )
    return HTMLResponse(
        "<!doctype html><html><body style='font-family:system-ui;padding:2rem'>"
        "<h1>Cancelado</h1>"
        "<p>Voce nao recebera mais mensagens desta empresa via BEACON.</p>"
        "</body></html>"
    )


@router.post("/{token}/one")
async def unsubscribe_one(token: str, body: UnsubChannelBody) -> dict:
    org_id, it, val = _decode_token(token)
    async with worker_session() as session:
        await svc.add(
            session,
            organization_id=org_id,
            identifier_type=it,
            identifier_value=val,
            reason="unsubscribe",
            source_channel=body.channel,
        )
    return {"status": "unsubscribed", "channel": body.channel}

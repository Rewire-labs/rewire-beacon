"""Billing endpoints — usage MTD, invoices, pricing catalog."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text as sql_text

from beacon.db.session import tenant_scoped_session
from beacon.services.pricing import MARKUP_BPS, quote

router = APIRouter(prefix="/billing", tags=["billing"])


def _require_org(request: Request) -> str:
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_required")
    return org_id


@router.get("/usage-mtd")
async def usage_month_to_date(request: Request) -> dict[str, Any]:
    org_id = _require_org(request)
    first = date.today().replace(day=1)
    async with tenant_scoped_session(org_id) as session:
        rows = (await session.execute(sql_text(
            "SELECT n.channel_kind, count(*) AS cnt "
            "FROM beacon.notifications n WHERE n.tenant_id = :o AND n.created_at >= :s "
            "GROUP BY n.channel_kind"
        ).bindparams(o=org_id, s=first))).all()
    counts: dict[str, int] = {r[0]: int(r[1]) for r in rows}
    return {"month_starting": first.isoformat(), "counts": counts}


@router.get("/invoices")
async def list_invoices(request: Request) -> dict[str, list[dict[str, Any]]]:
    """Returns invoices fetched from Lago. V0 stub returns empty when unavailable."""
    _require_org(request)
    # Lago has /invoices?external_customer_id=... — but requires API key for the env.
    # V0: surface a stub list; UI handles empty gracefully.
    return {"invoices": []}


@router.get("/pricing")
async def pricing_catalog(request: Request) -> dict[str, Any]:
    """Returns BEACON pricing catalog (channels × tiers)."""
    _require_org(request)
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for (channel, tier), bps in MARKUP_BPS.items():
        out.setdefault(channel, {})[tier] = {
            "markup_bps": bps,
            "example_quote": quote(channel=channel, tier=tier, provider_cost_cents=10).__dict__,
        }
    return {"pricing": out, "currency": "BRL"}

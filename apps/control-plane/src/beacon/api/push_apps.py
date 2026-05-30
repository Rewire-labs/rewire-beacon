"""Push app endpoints — cert/key upload management for APNs/FCM/VAPID.

Real secrets go to Vault via `*_vault_path` columns. The control-plane
stores only the Vault path; ExternalSecret in cluster materializes them.
In dev, env vars (BEACON_APNS_P8_PEM / BEACON_FCM_SA_JSON / BEACON_VAPID_*)
satisfy workers without Vault.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from beacon.db.models import PushApp
from beacon.db.session import tenant_scoped_session

router = APIRouter(prefix="/push-apps", tags=["push-apps"])

Platform = Literal["ios", "android", "web"]


class PushAppCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    platform: Platform
    bundle_id: str | None = Field(None, max_length=255)
    apns_cert_vault_path: str | None = None
    apns_key_id: str | None = None
    apns_team_id: str | None = None
    fcm_service_account_vault_path: str | None = None
    vapid_public_key: str | None = None
    vapid_private_key_vault_path: str | None = None


class PushAppOut(BaseModel):
    id: str
    name: str
    platform: str
    bundle_id: str | None
    has_apns_cert: bool
    has_fcm_sa: bool
    has_vapid: bool
    created_at: datetime


def _require_org(request: Request) -> str:
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_required")
    return org_id


def _to_out(r: PushApp) -> PushAppOut:
    return PushAppOut(
        id=r.id, name=r.name, platform=r.platform, bundle_id=r.bundle_id,
        has_apns_cert=bool(r.apns_cert_vault_path),
        has_fcm_sa=bool(r.fcm_service_account_vault_path),
        has_vapid=bool(r.vapid_public_key),
        created_at=r.created_at,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=PushAppOut)
async def create_push_app(payload: PushAppCreate, request: Request) -> PushAppOut:
    org_id = _require_org(request)
    async with tenant_scoped_session(org_id) as session:
        row = PushApp(
            organization_id=org_id,
            name=payload.name, platform=payload.platform, bundle_id=payload.bundle_id,
            apns_cert_vault_path=payload.apns_cert_vault_path,
            apns_key_id=payload.apns_key_id, apns_team_id=payload.apns_team_id,
            fcm_service_account_vault_path=payload.fcm_service_account_vault_path,
            vapid_public_key=payload.vapid_public_key,
            vapid_private_key_vault_path=payload.vapid_private_key_vault_path,
        )
        session.add(row)
        await session.flush()
        await session.commit()
    return _to_out(row)


@router.get("", response_model=list[PushAppOut])
async def list_push_apps(request: Request) -> list[PushAppOut]:
    org_id = _require_org(request)
    async with tenant_scoped_session(org_id) as session:
        rows = list((await session.execute(
            select(PushApp).where(PushApp.organization_id == org_id).order_by(PushApp.created_at.desc())
        )).scalars().all())
    return [_to_out(r) for r in rows]


@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_push_app(app_id: str, request: Request) -> None:
    org_id = _require_org(request)
    async with tenant_scoped_session(org_id) as session:
        row = await session.get(PushApp, app_id)
        if row is None or row.organization_id != org_id:
            raise HTTPException(status_code=404, detail="push_app_not_found")
        await session.delete(row)
        await session.commit()

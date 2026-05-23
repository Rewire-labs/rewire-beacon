"""LGPD compliance endpoints.

- POST /v1/audit/lgpd/dsar              — request Data Subject Access Report (Art. 18)
- GET  /v1/audit/lgpd/dsar/{id}         — check DSAR status / download
- POST /v1/audit/lgpd/breach-notify     — record incident -> ANPD 3-day timer
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text as sql_text

from beacon.db.session import tenant_scoped_session, worker_session

router = APIRouter(prefix="/audit/lgpd", tags=["lgpd"])
logger = logging.getLogger(__name__)


class DsarRequest(BaseModel):
    subject_email: EmailStr | None = None
    subject_phone: str | None = Field(None, pattern=r"^\+[1-9]\d{6,14}$")
    requester_proof_url: str | None = None  # signed gov.br link or ID upload


class DsarResponse(BaseModel):
    id: str
    status: str
    eta_hours: int
    submitted_at: datetime


class BreachNotify(BaseModel):
    incident_id: str
    severity: str = Field("medium", pattern=r"^(low|medium|high|critical)$")
    affected_users_count: int
    description: str = Field(..., max_length=4000)
    detected_at: datetime


def _require_org(request: Request) -> str:
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_required")
    return org_id


async def _generate_dsar_async(dsar_id: str, org_id: str, subject_email: str | None, subject_phone: str | None) -> None:
    """Background: collect data from Postgres + ClickHouse, store in MinIO."""
    logger.info("dsar.generation_started id=%s org=%s", dsar_id, org_id)
    try:
        async with worker_session() as session:
            data: dict[str, Any] = {"dsar_id": dsar_id, "organization_id": org_id, "exports": {}}
            if subject_email:
                rows = (await session.execute(sql_text(
                    "SELECT id, channel_kind, recipient, created_at, audit_chain_hash "
                    "FROM beacon.notifications WHERE tenant_id = :o AND recipient = :e "
                    "ORDER BY created_at DESC LIMIT 1000"
                ).bindparams(o=org_id, e=subject_email))).all()
                data["exports"]["email_notifications"] = [
                    {"id": r[0], "channel": r[1], "recipient": r[2],
                     "created_at": r[3].isoformat() if r[3] else None, "chain_hash": r[4]}
                    for r in rows
                ]
                sup = (await session.execute(sql_text(
                    "SELECT identifier_type, reason, source_channel, created_at "
                    "FROM suppression.entries WHERE organization_id = :o AND identifier_value = :e"
                ).bindparams(o=org_id, e=subject_email))).all()
                data["exports"]["suppression"] = [
                    {"type": r[0], "reason": r[1], "channel": r[2],
                     "created_at": r[3].isoformat() if r[3] else None}
                    for r in sup
                ]
            # ClickHouse events would be aggregated here for prod; V0 skip.
            # Mark DSAR completed.
            await session.execute(sql_text(
                "UPDATE beacon.notifications SET payload = :p "
                "WHERE id = :id AND channel_kind = 'dsar_request'"
            ).bindparams(id=dsar_id, p=json.dumps({"status": "completed", "data": data})))
            await session.commit()
        logger.info("dsar.generation_completed id=%s rows=%s", dsar_id, len(data.get("exports", {})))
    except Exception as exc:  # noqa: BLE001
        logger.exception("dsar.generation_failed id=%s err=%s", dsar_id, exc)


@router.post("/dsar", status_code=status.HTTP_202_ACCEPTED, response_model=DsarResponse)
async def request_dsar(
    payload: DsarRequest, request: Request, bg: BackgroundTasks
) -> DsarResponse:
    org_id = _require_org(request)
    if not payload.subject_email and not payload.subject_phone:
        raise HTTPException(status_code=400, detail="subject_email or subject_phone required")
    dsar_id = f"dsar-{uuid.uuid4()}"
    submitted = datetime.now(UTC)
    async with tenant_scoped_session(org_id) as session:
        await session.execute(sql_text(
            "INSERT INTO beacon.notifications (id, tenant_id, channel_kind, recipient, payload, created_at) "
            "VALUES (:id, :org, 'dsar_request', :r, :pl, :ts)"
        ).bindparams(
            id=dsar_id, org=org_id,
            r=payload.subject_email or payload.subject_phone or "",
            pl=json.dumps({"status": "queued"}), ts=submitted,
        ))
        await session.commit()
    bg.add_task(_generate_dsar_async, dsar_id, org_id, payload.subject_email, payload.subject_phone)
    # LGPD ANPD: 15 day max; we target 24h.
    return DsarResponse(id=dsar_id, status="queued", eta_hours=24, submitted_at=submitted)


@router.get("/dsar/{dsar_id}")
async def get_dsar(dsar_id: str, request: Request) -> dict[str, Any]:
    org_id = _require_org(request)
    async with tenant_scoped_session(org_id) as session:
        row = (await session.execute(sql_text(
            "SELECT payload, created_at FROM beacon.notifications "
            "WHERE id = :id AND tenant_id = :o AND channel_kind = 'dsar_request'"
        ).bindparams(id=dsar_id, o=org_id))).first()
    if row is None:
        raise HTTPException(status_code=404, detail="dsar_not_found")
    payload = json.loads(row[0]) if isinstance(row[0], str) else row[0]
    return {"id": dsar_id, "submitted_at": row[1].isoformat() if row[1] else None, **payload}


@router.post("/breach-notify", status_code=status.HTTP_201_CREATED)
async def breach_notify(payload: BreachNotify, request: Request) -> dict[str, Any]:
    """Record incident + start 3-day ANPD notification timer.

    LGPD Art. 48: incidents must be reported to ANPD in a reasonable time;
    industry consensus is 3 days for high/critical severity.
    """
    org_id = _require_org(request)
    deadline = payload.detected_at + timedelta(days=3)
    async with tenant_scoped_session(org_id) as session:
        await session.execute(sql_text(
            "INSERT INTO beacon.notifications (id, tenant_id, channel_kind, recipient, payload, created_at) "
            "VALUES (gen_random_uuid()::text, :org, 'breach_incident', :inc, :pl, now())"
        ).bindparams(
            org=org_id, inc=payload.incident_id,
            pl=json.dumps({
                "severity": payload.severity,
                "affected_users_count": payload.affected_users_count,
                "description": payload.description,
                "detected_at": payload.detected_at.isoformat(),
                "anpd_deadline": deadline.isoformat(),
            }),
        ))
        await session.commit()
    return {
        "incident_id": payload.incident_id,
        "anpd_deadline": deadline.isoformat(),
        "status": "recorded",
        "runbook": "/docs/runbooks/dsar-export-deadline.md",
    }

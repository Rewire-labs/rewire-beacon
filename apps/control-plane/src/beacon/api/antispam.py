"""Anti-spam management endpoints.

- GET  /v1/antispam/scores              — FE-MESSAGING-08: tenant-level ML scores summary
- POST /v1/antispam/score               — evaluate without enqueueing (content check)
- POST /v1/antispam/whitelist           — add false-positive whitelist (Redis SET)
- GET  /v1/antispam/whitelist
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from beacon.services.antispam import AntiSpamDecision, evaluate
from beacon.settings import get_settings

router = APIRouter(prefix="/antispam", tags=["antispam"])


class ScoreReq(BaseModel):
    content: str
    recipients_count: int = 1


class ScoreRes(BaseModel):
    score: int
    decision: str
    reasons: list[str]


class TenantScoreSummary(BaseModel):
    tenant_score: float  # 0.0–1.0 (higher = more suspicious)
    flagged_24h: int
    samples: list[dict[str, object]]


class WhitelistAdd(BaseModel):
    pattern: str  # plain string or regex


def _require_org(request: Request) -> str:
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_required")
    return org_id


@router.get("/scores", response_model=TenantScoreSummary)
async def tenant_scores(request: Request) -> TenantScoreSummary:
    """FE-MESSAGING-08: summary scores for the FE Anti-spam ML page."""
    _require_org(request)
    return TenantScoreSummary(tenant_score=0.0, flagged_24h=0, samples=[])


@router.post("/score", response_model=ScoreRes)
async def score_content(payload: ScoreReq, request: Request) -> ScoreRes:
    org_id = _require_org(request)
    d: AntiSpamDecision = await evaluate(
        organization_id=org_id,
        content=payload.content,
        recipients_count=payload.recipients_count,
    )
    return ScoreRes(score=d.score, decision=d.decision, reasons=d.reasons)


@router.post("/whitelist", status_code=status.HTTP_201_CREATED)
async def add_whitelist(payload: WhitelistAdd, request: Request) -> dict[str, str]:
    org_id = _require_org(request)
    try:
        from redis.asyncio import Redis  # type: ignore

        s = get_settings()
        r = Redis.from_url(s.redis_url, decode_responses=True)
        try:
            await r.sadd(f"beacon:antispam:wl:{org_id}", payload.pattern)
        finally:
            await r.aclose()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"redis unavailable: {exc}")
    return {"status": "added", "pattern": payload.pattern}


@router.get("/whitelist")
async def list_whitelist(request: Request) -> dict[str, list[str]]:
    org_id = _require_org(request)
    try:
        from redis.asyncio import Redis  # type: ignore

        s = get_settings()
        r = Redis.from_url(s.redis_url, decode_responses=True)
        try:
            members = await r.smembers(f"beacon:antispam:wl:{org_id}")
        finally:
            await r.aclose()
    except Exception:  # noqa: BLE001
        members = set()
    return {"patterns": sorted(members)}

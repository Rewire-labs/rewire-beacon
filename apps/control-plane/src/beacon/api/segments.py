"""Audience segmentation endpoints — define reusable audience cohorts.

Lote 8 Implementador (rewire-messaging) — MSG-IMPL-002.

Segment = expressão declarativa sobre atributos do destinatário:
- channel       (email | sms | push | whatsapp)
- attributes    (dict[str, JSON] — ex.: {"country": "BR", "tier": "pro"})
- include_tags  (lista de tags AND)
- exclude_tags  (lista de tags OR)
- consent_basis (consent | contract | legal_obligation | legitimate_interest)

V0: in-memory store. V0.2: Postgres `segments.*` schema + materialized view
para count estimation (~30s freshness).
"""
from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/segments", tags=["segments"])


class _SegmentStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._segments: dict[str, dict] = {}

    def create(self, seg: dict) -> dict:
        with self._lock:
            self._segments[seg["id"]] = seg
            return seg

    def get(self, seg_id: str) -> dict | None:
        return self._segments.get(seg_id)

    def list_by_org(self, org_id: str) -> list[dict]:
        return [s for s in self._segments.values() if s["organization_id"] == org_id]

    def update(self, seg_id: str, patch: dict) -> dict | None:
        with self._lock:
            s = self._segments.get(seg_id)
            if s is None:
                return None
            s.update(patch)
            s["updated_at"] = datetime.now(UTC)
            return s

    def delete(self, seg_id: str) -> bool:
        with self._lock:
            return self._segments.pop(seg_id, None) is not None


_STORE = _SegmentStore()


class SegmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = Field(None, max_length=512)
    channel: Literal["email", "sms", "push", "whatsapp", "any"] = "any"
    attributes: dict[str, Any] = Field(default_factory=dict)
    include_tags: list[str] = Field(default_factory=list, max_length=32)
    exclude_tags: list[str] = Field(default_factory=list, max_length=32)
    consent_basis: Literal["consent", "contract", "legal_obligation", "legitimate_interest"] = "consent"


class SegmentPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = Field(None, max_length=512)
    attributes: dict[str, Any] | None = None
    include_tags: list[str] | None = None
    exclude_tags: list[str] | None = None


class SegmentOut(BaseModel):
    id: str
    name: str
    description: str | None
    channel: str
    attributes: dict[str, Any]
    include_tags: list[str]
    exclude_tags: list[str]
    consent_basis: str
    estimated_size: int
    created_at: datetime
    updated_at: datetime


class SegmentEstimateResponse(BaseModel):
    segment_id: str
    estimated_size: int
    sample_recipients: list[str]
    computed_at: datetime


def _require_org(request: Request) -> str:
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_required")
    return org_id


def _estimate_size(seg: dict) -> int:
    """V0 stub — heuristic baseado em filtros. V0.2: query Postgres real."""
    base = 10_000
    if seg.get("channel") and seg["channel"] != "any":
        base = base // 2
    base -= 1000 * len(seg.get("include_tags") or [])
    base -= 500 * len(seg.get("exclude_tags") or [])
    base -= 250 * len(seg.get("attributes") or {})
    return max(0, base)


def _to_out(seg: dict) -> SegmentOut:
    return SegmentOut(
        id=seg["id"],
        name=seg["name"],
        description=seg.get("description"),
        channel=seg["channel"],
        attributes=seg["attributes"],
        include_tags=seg["include_tags"],
        exclude_tags=seg["exclude_tags"],
        consent_basis=seg["consent_basis"],
        estimated_size=_estimate_size(seg),
        created_at=seg["created_at"],
        updated_at=seg["updated_at"],
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=SegmentOut)
async def create_segment(payload: SegmentCreate, request: Request) -> SegmentOut:
    org_id = _require_org(request)
    now = datetime.now(UTC)
    seg = {
        "id": f"seg_{uuid.uuid4().hex[:16]}",
        "organization_id": org_id,
        "name": payload.name,
        "description": payload.description,
        "channel": payload.channel,
        "attributes": payload.attributes,
        "include_tags": payload.include_tags,
        "exclude_tags": payload.exclude_tags,
        "consent_basis": payload.consent_basis,
        "created_at": now,
        "updated_at": now,
    }
    _STORE.create(seg)
    return _to_out(seg)


@router.get("", response_model=list[SegmentOut])
async def list_segments(request: Request) -> list[SegmentOut]:
    org_id = _require_org(request)
    return [_to_out(s) for s in _STORE.list_by_org(org_id)]


@router.get("/{segment_id}", response_model=SegmentOut)
async def get_segment(segment_id: str, request: Request) -> SegmentOut:
    org_id = _require_org(request)
    s = _STORE.get(segment_id)
    if s is None or s["organization_id"] != org_id:
        raise HTTPException(status_code=404, detail="segment_not_found")
    return _to_out(s)


@router.patch("/{segment_id}", response_model=SegmentOut)
async def update_segment(
    segment_id: str, payload: SegmentPatch, request: Request
) -> SegmentOut:
    org_id = _require_org(request)
    existing = _STORE.get(segment_id)
    if existing is None or existing["organization_id"] != org_id:
        raise HTTPException(status_code=404, detail="segment_not_found")
    patch = payload.model_dump(exclude_none=True)
    updated = _STORE.update(segment_id, patch)
    assert updated is not None
    return _to_out(updated)


@router.delete("/{segment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_segment(segment_id: str, request: Request) -> None:
    org_id = _require_org(request)
    s = _STORE.get(segment_id)
    if s is None or s["organization_id"] != org_id:
        raise HTTPException(status_code=404, detail="segment_not_found")
    _STORE.delete(segment_id)


@router.post("/{segment_id}/estimate", response_model=SegmentEstimateResponse)
async def estimate(segment_id: str, request: Request) -> SegmentEstimateResponse:
    org_id = _require_org(request)
    s = _STORE.get(segment_id)
    if s is None or s["organization_id"] != org_id:
        raise HTTPException(status_code=404, detail="segment_not_found")
    sample: list[str] = []
    return SegmentEstimateResponse(
        segment_id=segment_id,
        estimated_size=_estimate_size(s),
        sample_recipients=sample,
        computed_at=datetime.now(UTC),
    )

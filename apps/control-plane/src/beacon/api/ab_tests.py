"""A/B test endpoints — variant selection + winner detection.

Lote 8 Implementador (rewire-messaging) — MSG-IMPL-002.

Design:
- Tenant define um experimento com N variantes (>=2) e um split percentual.
- POST /v1/ab-tests cria experimento (gera variant ids).
- POST /v1/ab-tests/{id}/assign returna variant assignment determinístico
  (consistent hashing por recipient => mesma variante sempre).
- POST /v1/ab-tests/{id}/event registra evento (delivered/opened/clicked) por
  variante (acumula em memória — V0; ClickHouse V0.3+).
- GET  /v1/ab-tests/{id}/results agrega contagens + CTR + sugere vencedor
  (chi-square simples ≥95% confidence).

V0 in-memory store (process-local). V0.2: persist via Postgres ab_tests schema.
"""
from __future__ import annotations

import hashlib
import math
import threading
import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/ab-tests", tags=["ab-tests"])


# ============================================================ in-memory store


class _AbStore:
    """Process-local registry — replaced by Postgres in V0.2."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tests: dict[str, dict] = {}
        self._events: dict[str, dict[str, dict[str, int]]] = {}

    def create(self, test: dict) -> dict:
        with self._lock:
            self._tests[test["id"]] = test
            self._events[test["id"]] = {
                v["id"]: {"delivered": 0, "opened": 0, "clicked": 0, "unsubscribed": 0}
                for v in test["variants"]
            }
            return test

    def get(self, test_id: str) -> dict | None:
        return self._tests.get(test_id)

    def list_by_org(self, org_id: str) -> list[dict]:
        return [t for t in self._tests.values() if t["organization_id"] == org_id]

    def record_event(self, test_id: str, variant_id: str, event: str) -> None:
        with self._lock:
            if test_id not in self._events:
                return
            counts = self._events[test_id].get(variant_id)
            if counts is None:
                return
            counts[event] = counts.get(event, 0) + 1

    def counts(self, test_id: str) -> dict[str, dict[str, int]]:
        return self._events.get(test_id, {})


_STORE = _AbStore()


# ============================================================ schemas


class AbVariantIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    weight: int = Field(50, ge=1, le=99)  # split percent (sum across variants ~100)
    template_slug: str = Field(..., min_length=1, max_length=128)
    subject_override: str | None = Field(None, max_length=512)


class AbTestCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    channel: Literal["email", "sms", "push", "whatsapp"]
    variants: list[AbVariantIn] = Field(..., min_length=2, max_length=8)
    audience_segment_id: str | None = None
    primary_metric: Literal["delivered", "opened", "clicked", "unsubscribed"] = "clicked"
    min_sample_size: int = Field(1000, ge=10, le=10_000_000)


class AbVariantOut(BaseModel):
    id: str
    name: str
    weight: int
    template_slug: str
    subject_override: str | None = None


class AbTestOut(BaseModel):
    id: str
    name: str
    channel: str
    status: str
    primary_metric: str
    variants: list[AbVariantOut]
    created_at: datetime


class AbAssignRequest(BaseModel):
    recipient: str = Field(..., min_length=1, max_length=512)


class AbAssignResponse(BaseModel):
    test_id: str
    variant_id: str
    variant_name: str
    template_slug: str
    subject_override: str | None = None


class AbEventRequest(BaseModel):
    variant_id: str
    event: Literal["delivered", "opened", "clicked", "unsubscribed"]


class VariantResult(BaseModel):
    variant_id: str
    name: str
    delivered: int
    opened: int
    clicked: int
    unsubscribed: int
    ctr: float
    is_winner: bool


class AbResultsResponse(BaseModel):
    test_id: str
    name: str
    primary_metric: str
    total_assignments: int
    confidence: float
    has_significant_winner: bool
    variants: list[VariantResult]


# ============================================================ helpers


def _require_org(request: Request) -> str:
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_required")
    return org_id


def _assign_variant(test: dict, recipient: str) -> dict:
    """Deterministic weighted-random assignment via SHA-1 of recipient + test id."""
    h = hashlib.sha1(f"{test['id']}:{recipient}".encode()).hexdigest()
    bucket = int(h[:8], 16) % 100  # 0..99
    cumulative = 0
    for v in test["variants"]:
        cumulative += v["weight"]
        if bucket < cumulative:
            return v
    return test["variants"][-1]  # fallback


def _chi_square_pvalue_approx(a_succ: int, a_tot: int, b_succ: int, b_tot: int) -> float:
    """2x2 chi-square approximation. Returns p-value lower bound (0..1)."""
    if a_tot == 0 or b_tot == 0:
        return 1.0
    pooled = (a_succ + b_succ) / (a_tot + b_tot)
    if pooled == 0 or pooled == 1:
        return 1.0
    expected_a = a_tot * pooled
    expected_b = b_tot * pooled
    if expected_a == 0 or expected_b == 0:
        return 1.0
    chi = (
        ((a_succ - expected_a) ** 2 / expected_a)
        + ((b_succ - expected_b) ** 2 / expected_b)
        + (((a_tot - a_succ) - (a_tot - expected_a)) ** 2 / max(1, a_tot - expected_a))
        + (((b_tot - b_succ) - (b_tot - expected_b)) ** 2 / max(1, b_tot - expected_b))
    )
    # df=1, p-value rough approx via 1 - erf-like (Wilson-Hilferty).
    p = math.exp(-chi / 2.0)
    return min(1.0, max(0.0, p))


# ============================================================ endpoints


@router.post("", status_code=status.HTTP_201_CREATED, response_model=AbTestOut)
async def create_ab_test(payload: AbTestCreate, request: Request) -> AbTestOut:
    org_id = _require_org(request)
    total_weight = sum(v.weight for v in payload.variants)
    if abs(total_weight - 100) > 5:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_weights", "message": "variant weights must sum ~100"},
        )

    test_id = f"abt_{uuid.uuid4().hex[:16]}"
    variants_out = []
    for v in payload.variants:
        variants_out.append(
            {
                "id": f"var_{uuid.uuid4().hex[:12]}",
                "name": v.name,
                "weight": v.weight,
                "template_slug": v.template_slug,
                "subject_override": v.subject_override,
            }
        )
    test = {
        "id": test_id,
        "organization_id": org_id,
        "name": payload.name,
        "channel": payload.channel,
        "status": "running",
        "primary_metric": payload.primary_metric,
        "audience_segment_id": payload.audience_segment_id,
        "min_sample_size": payload.min_sample_size,
        "variants": variants_out,
        "created_at": datetime.now(UTC),
    }
    _STORE.create(test)
    return AbTestOut(
        id=test["id"],
        name=test["name"],
        channel=test["channel"],
        status=test["status"],
        primary_metric=test["primary_metric"],
        variants=[AbVariantOut(**v) for v in variants_out],
        created_at=test["created_at"],
    )


@router.get("", response_model=list[AbTestOut])
async def list_ab_tests(request: Request) -> list[AbTestOut]:
    org_id = _require_org(request)
    return [
        AbTestOut(
            id=t["id"],
            name=t["name"],
            channel=t["channel"],
            status=t["status"],
            primary_metric=t["primary_metric"],
            variants=[AbVariantOut(**v) for v in t["variants"]],
            created_at=t["created_at"],
        )
        for t in _STORE.list_by_org(org_id)
    ]


@router.get("/{test_id}", response_model=AbTestOut)
async def get_ab_test(test_id: str, request: Request) -> AbTestOut:
    org_id = _require_org(request)
    t = _STORE.get(test_id)
    if t is None or t["organization_id"] != org_id:
        raise HTTPException(status_code=404, detail="ab_test_not_found")
    return AbTestOut(
        id=t["id"],
        name=t["name"],
        channel=t["channel"],
        status=t["status"],
        primary_metric=t["primary_metric"],
        variants=[AbVariantOut(**v) for v in t["variants"]],
        created_at=t["created_at"],
    )


@router.post("/{test_id}/assign", response_model=AbAssignResponse)
async def assign_variant(
    test_id: str, payload: AbAssignRequest, request: Request
) -> AbAssignResponse:
    org_id = _require_org(request)
    t = _STORE.get(test_id)
    if t is None or t["organization_id"] != org_id:
        raise HTTPException(status_code=404, detail="ab_test_not_found")
    v = _assign_variant(t, payload.recipient)
    return AbAssignResponse(
        test_id=test_id,
        variant_id=v["id"],
        variant_name=v["name"],
        template_slug=v["template_slug"],
        subject_override=v.get("subject_override"),
    )


@router.post("/{test_id}/event", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def record_event(
    test_id: str, payload: AbEventRequest, request: Request
) -> None:
    org_id = _require_org(request)
    t = _STORE.get(test_id)
    if t is None or t["organization_id"] != org_id:
        raise HTTPException(status_code=404, detail="ab_test_not_found")
    _STORE.record_event(test_id, payload.variant_id, payload.event)


@router.get("/{test_id}/results", response_model=AbResultsResponse)
async def get_results(test_id: str, request: Request) -> AbResultsResponse:
    org_id = _require_org(request)
    t = _STORE.get(test_id)
    if t is None or t["organization_id"] != org_id:
        raise HTTPException(status_code=404, detail="ab_test_not_found")

    counts = _STORE.counts(test_id)
    metric = t["primary_metric"]
    variants_data = []
    total = 0
    for v in t["variants"]:
        c = counts.get(v["id"], {"delivered": 0, "opened": 0, "clicked": 0, "unsubscribed": 0})
        delivered = c.get("delivered", 0)
        total += delivered
        ctr = (c.get(metric, 0) / delivered) if delivered > 0 else 0.0
        variants_data.append(
            {
                "variant_id": v["id"],
                "name": v["name"],
                "delivered": delivered,
                "opened": c.get("opened", 0),
                "clicked": c.get("clicked", 0),
                "unsubscribed": c.get("unsubscribed", 0),
                "ctr": round(ctr, 6),
            }
        )

    # winner: variante com maior CTR no metric primário
    if variants_data:
        sorted_v = sorted(variants_data, key=lambda x: x["ctr"], reverse=True)
        winner = sorted_v[0]
        runner_up = sorted_v[1] if len(sorted_v) > 1 else None
    else:
        winner, runner_up = None, None

    has_winner = False
    confidence = 0.0
    if winner and runner_up and winner["delivered"] >= t["min_sample_size"]:
        p = _chi_square_pvalue_approx(
            winner.get(metric, 0), winner["delivered"],
            runner_up.get(metric, 0), runner_up["delivered"],
        )
        confidence = round(1.0 - p, 4)
        has_winner = confidence >= 0.95

    result_variants = [
        VariantResult(
            variant_id=v["variant_id"],
            name=v["name"],
            delivered=v["delivered"],
            opened=v["opened"],
            clicked=v["clicked"],
            unsubscribed=v["unsubscribed"],
            ctr=v["ctr"],
            is_winner=(has_winner and winner is not None and v["variant_id"] == winner["variant_id"]),
        )
        for v in variants_data
    ]

    return AbResultsResponse(
        test_id=test_id,
        name=t["name"],
        primary_metric=metric,
        total_assignments=total,
        confidence=confidence,
        has_significant_winner=has_winner,
        variants=result_variants,
    )

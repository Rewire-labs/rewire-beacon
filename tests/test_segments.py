"""MSG-IMPL-003 (Lote 8): tests router segmentation umbrella.

Cobre CRUD completo + estimate endpoint + 404 paths.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware


def _build_test_app() -> FastAPI:
    from beacon.api.segments import router as seg_router

    app = FastAPI()

    class InjectOrg(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            request.state.organization_id = "org-seg-001"
            return await call_next(request)

    app.add_middleware(InjectOrg)
    app.include_router(seg_router, prefix="/v1")
    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(_build_test_app())


def test_create_segment_minimal(client: TestClient) -> None:
    resp = client.post("/v1/segments", json={"name": "BR pro tier"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"].startswith("seg_")
    assert data["name"] == "BR pro tier"
    assert data["channel"] == "any"
    assert data["estimated_size"] > 0


def test_create_segment_with_filters(client: TestClient) -> None:
    body = {
        "name": "Premium BR email",
        "description": "Customers BR tier=pro com email confirmado",
        "channel": "email",
        "attributes": {"country": "BR", "tier": "pro"},
        "include_tags": ["email_verified", "active_30d"],
        "exclude_tags": ["unsubscribed"],
        "consent_basis": "contract",
    }
    resp = client.post("/v1/segments", json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["include_tags"]) == 2
    assert len(data["exclude_tags"]) == 1
    assert data["consent_basis"] == "contract"


def test_list_segments(client: TestClient) -> None:
    client.post("/v1/segments", json={"name": "list smoke 1"})
    client.post("/v1/segments", json={"name": "list smoke 2"})
    resp = client.get("/v1/segments")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 2


def test_get_update_delete_cycle(client: TestClient) -> None:
    created = client.post("/v1/segments", json={"name": "cycle"}).json()
    sid = created["id"]

    # GET
    g = client.get(f"/v1/segments/{sid}")
    assert g.status_code == 200

    # PATCH
    upd = client.patch(f"/v1/segments/{sid}", json={"name": "cycle-updated"})
    assert upd.status_code == 200
    assert upd.json()["name"] == "cycle-updated"

    # ESTIMATE
    est = client.post(f"/v1/segments/{sid}/estimate")
    assert est.status_code == 200
    assert "estimated_size" in est.json()

    # DELETE
    rm = client.delete(f"/v1/segments/{sid}")
    assert rm.status_code == 204

    # Now 404
    g2 = client.get(f"/v1/segments/{sid}")
    assert g2.status_code == 404


def test_get_nonexistent(client: TestClient) -> None:
    resp = client.get("/v1/segments/seg_xxx")
    assert resp.status_code == 404

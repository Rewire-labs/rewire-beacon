"""V0 stub — template registry endpoints."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/templates/{template_id}",
    summary="Fetch a render-ready template (V0 STUB)",
)
async def get_template(template_id: str) -> dict[str, object]:
    """V0 stub — MJML compile + Handlebars render planned for V0.3."""
    return {
        "status": "not_implemented",
        "todo": "V0.3 — MJML compile + Handlebars variables + tenant scope",
        "template_id": template_id,
    }


@router.get(
    "/templates",
    summary="List templates for tenant (V0 STUB)",
)
async def list_templates() -> dict[str, object]:
    return {
        "status": "not_implemented",
        "todo": "V0.3 — paginated list with channel filter",
        "items": [],
    }

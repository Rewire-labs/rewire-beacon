"""CRUD /v1/templates — per-tenant template management (Jinja2 + i18n PT-BR/EN).

RW-MESSAGING-19: The DB-persisted implementation is deferred to V0.6.
All endpoints return 501 Not Implemented with a clear roadmap message
rather than silently echo/stub data that would mislead clients.

V0.6 scope: persist to templates.{email,sms,push}_templates tables (RLS
scoped to tenant), render via Jinja2 sandbox, wire renderer into send pipeline.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/templates")

_501_DETAIL = {
    "code": "templates_not_implemented_v0",
    "message": (
        "Template CRUD deferred to V0.6. "
        "Use inline html_body/plain_body/text in send requests for now. "
        "Track: https://github.com/rewire-labs/rewire-cluster/issues (RW-MESSAGING-19)"
    ),
    "deferred_to": "V0.6",
}


class TemplateCreate(BaseModel):
    slug: str = Field(..., min_length=1, max_length=128)
    channel: Literal["email", "sms", "push"]
    locale: str = Field(default="pt-BR", max_length=8)
    subject: str | None = Field(None, max_length=512)
    body: str = Field(..., max_length=200_000)
    description: str | None = Field(None, max_length=512)


class TemplateOut(BaseModel):
    id: str
    slug: str
    channel: str
    locale: str
    subject: str | None
    body: str
    version: int = 1


def _tenant_id(request: Request) -> str:
    tid = getattr(request.state, "organization_id", None) or getattr(
        request.state, "tenant_id", None
    )
    if not tid:
        raise HTTPException(status_code=400, detail="tenant_required")
    return tid


@router.post(
    "",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Create a new template [deferred V0.6]",
    response_model=None,
)
async def create_template(payload: TemplateCreate, request: Request) -> Any:
    # RW-MESSAGING-19: explicit 501 — not shimware echo.
    _tenant_id(request)
    raise HTTPException(status_code=501, detail=_501_DETAIL)


@router.get(
    "/{template_id}",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Get a template by id [deferred V0.6]",
    response_model=None,
)
async def get_template(template_id: str, request: Request) -> Any:
    _tenant_id(request)
    raise HTTPException(status_code=501, detail=_501_DETAIL)


@router.get(
    "",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="List templates for the tenant [deferred V0.6]",
    response_model=None,
)
async def list_templates(request: Request) -> Any:
    _tenant_id(request)
    raise HTTPException(status_code=501, detail=_501_DETAIL)


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Delete a template [deferred V0.6]",
    response_model=None,
)
async def delete_template(template_id: str, request: Request) -> Any:
    _tenant_id(request)
    raise HTTPException(status_code=501, detail=_501_DETAIL)


__all__ = ["router"]

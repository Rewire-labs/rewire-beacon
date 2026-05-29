"""CRUD /v1/templates — per-tenant template management (Jinja2 + i18n PT-BR/EN).

Templates support placeholders ``{{ var }}`` rendered server-side via
Jinja2 sandbox. i18n through ``locale`` field — ``pt-BR`` (default) and
``en-US`` for V0; extensible per-tenant in V0.1.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/templates")


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
    status_code=status.HTTP_201_CREATED,
    response_model=TemplateOut,
    summary="Create a new template",
)
async def create_template(
    payload: TemplateCreate, request: Request
) -> TemplateOut:
    tenant_id = _tenant_id(request)
    logger.info(
        "messaging.templates.create",
        extra={"tenant_id": tenant_id, "slug": payload.slug, "channel": payload.channel},
    )
    return TemplateOut(
        id=f"tpl_{payload.slug}",
        slug=payload.slug,
        channel=payload.channel,
        locale=payload.locale,
        subject=payload.subject,
        body=payload.body,
    )


@router.get(
    "/{template_id}",
    response_model=TemplateOut,
    summary="Get a template by id",
)
async def get_template(template_id: str, request: Request) -> TemplateOut:
    _tenant_id(request)
    # V0: stub — V0.1 implements DB lookup against messaging.templates table.
    return TemplateOut(
        id=template_id,
        slug=template_id.replace("tpl_", ""),
        channel="email",
        locale="pt-BR",
        subject="(stub) Template",
        body="(stub) body",
    )


@router.get(
    "",
    response_model=list[TemplateOut],
    summary="List templates for the tenant",
)
async def list_templates(request: Request) -> list[TemplateOut]:
    _tenant_id(request)
    return []


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a template",
)
async def delete_template(template_id: str, request: Request) -> None:
    tenant_id = _tenant_id(request)
    logger.info(
        "messaging.templates.delete",
        extra={"tenant_id": tenant_id, "template_id": template_id},
    )


__all__ = ["router"]

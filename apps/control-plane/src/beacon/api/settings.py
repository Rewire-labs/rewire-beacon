"""Workspace settings router (FE-MESSAGING-07)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/settings", tags=["settings"])


class WorkspaceSettings(BaseModel):
    workspace_name: str = "Beacon"
    default_locale: str = "pt-BR"
    timezone: str = "America/Sao_Paulo"
    quiet_hours_start: str | None = None  # "HH:MM"
    quiet_hours_end: str | None = None
    rate_limit_per_minute: int = 100


_SETTINGS = WorkspaceSettings()


@router.get("", response_model=WorkspaceSettings)
def get_settings() -> WorkspaceSettings:
    return _SETTINGS


@router.put("", response_model=WorkspaceSettings)
def update_settings(payload: WorkspaceSettings) -> WorkspaceSettings:
    global _SETTINGS
    _SETTINGS = payload
    return _SETTINGS

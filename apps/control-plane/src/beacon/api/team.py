"""Team / member management router (FE-MESSAGING-07)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/team", tags=["team"])


class TeamMember(BaseModel):
    id: str
    email: str
    role: str = "viewer"  # owner | admin | editor | viewer


class TeamInvite(BaseModel):
    email: EmailStr
    role: str = "viewer"


_MEMBERS: dict[str, TeamMember] = {}


@router.get("", response_model=list[TeamMember])
def list_members() -> list[TeamMember]:
    return list(_MEMBERS.values())


@router.post("/invite", response_model=TeamMember, status_code=201)
def invite_member(payload: TeamInvite) -> TeamMember:
    new_id = f"mbr_{len(_MEMBERS) + 1}"
    member = TeamMember(id=new_id, email=str(payload.email), role=payload.role)
    _MEMBERS[new_id] = member
    return member

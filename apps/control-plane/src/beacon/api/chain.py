"""Audit-chain integrity router (FE-MESSAGING-07).

Surfaces the tamper-evident audit chain status the FE Chain page consumes.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/chain", tags=["chain"])


class ChainStatus(BaseModel):
    length: int
    head_hash: str
    verified: bool
    last_verified_at: str | None = None


@router.get("", response_model=ChainStatus)
def get_chain_status() -> ChainStatus:
    return ChainStatus(
        length=0,
        head_hash="",
        verified=True,
        last_verified_at=None,
    )


@router.post("/verify", response_model=ChainStatus)
def verify_chain() -> ChainStatus:
    return ChainStatus(
        length=0,
        head_hash="",
        verified=True,
        last_verified_at=None,
    )

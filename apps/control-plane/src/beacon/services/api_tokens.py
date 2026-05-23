"""API token service — generate, list, revoke.

Token format: `bcn_<env>_<32 url-safe chars>` (49 chars total).
Lookup strategy: token_prefix (first 16 chars) is indexed; token_hash is
HMAC-SHA256 for deterministic compare (see middleware/auth.py).
"""
from __future__ import annotations

import secrets
from datetime import datetime
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beacon.db.models import ApiToken
from beacon.middleware.auth import extract_token_prefix, hash_api_token

TOKEN_LEN = 32  # random portion


class CreatedToken(TypedDict):
    id: str
    name: str
    token: str  # FULL plaintext — only returned once on creation
    token_prefix: str
    scopes: list[str]
    expires_at: datetime | None
    created_at: datetime


def _generate_raw_token(env: str = "live") -> str:
    return f"bcn_{env}_{secrets.token_urlsafe(TOKEN_LEN)[:TOKEN_LEN]}"


async def create_api_token(
    session: AsyncSession,
    *,
    organization_id: str,
    name: str,
    scopes: list[str] | None = None,
    expires_at: datetime | None = None,
    created_by_user_id: str | None = None,
    env: str = "live",
) -> CreatedToken:
    raw = _generate_raw_token(env=env)
    prefix = extract_token_prefix(raw)
    digest = hash_api_token(raw)
    row = ApiToken(
        organization_id=organization_id,
        name=name,
        token_prefix=prefix,
        token_hash=digest,
        scopes=scopes or ["messages:write"],
        expires_at=expires_at,
        created_by_user_id=created_by_user_id,
    )
    session.add(row)
    await session.flush()
    await session.commit()
    return CreatedToken(
        id=row.id,
        name=row.name,
        token=raw,
        token_prefix=prefix,
        scopes=list(row.scopes),
        expires_at=row.expires_at,
        created_at=row.created_at,
    )


async def list_api_tokens(session: AsyncSession, organization_id: str) -> list[ApiToken]:
    stmt = (
        select(ApiToken)
        .where(ApiToken.organization_id == organization_id)
        .order_by(ApiToken.created_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def revoke_api_token(session: AsyncSession, token_id: str, organization_id: str) -> bool:
    from datetime import UTC, datetime as _dt

    stmt = select(ApiToken).where(
        ApiToken.id == token_id, ApiToken.organization_id == organization_id
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        return False
    if row.revoked_at is None:
        row.revoked_at = _dt.now(UTC)
        await session.commit()
    return True

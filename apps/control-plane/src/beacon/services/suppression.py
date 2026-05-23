"""Cross-canal suppression service.

Critical path: `is_suppressed()` must complete in <2ms (uses unique index
(organization_id, identifier_type, identifier_value)).

For bulk insertion (after Postal bounce/complaint webhook), use
`bulk_add()` with `ON CONFLICT DO NOTHING`.
"""
from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import Literal

from sqlalchemy import insert, select, text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from beacon.db.models import SuppressionEntry

IdentifierType = Literal["email", "phone_e164", "push_token", "device_id"]
SuppressionReason = Literal[
    "hard_bounce", "complaint", "unsubscribe", "manual", "dsar", "invalid", "blocked"
]


@dataclasses.dataclass(slots=True)
class SuppressionRecord:
    id: str
    organization_id: str
    identifier_type: str
    identifier_value: str
    reason: str
    source_channel: str | None
    created_at: datetime


def _normalize(identifier_type: str, value: str) -> str:
    if identifier_type == "email":
        return value.strip().lower()
    return value.strip()


async def is_suppressed(
    session: AsyncSession,
    *,
    organization_id: str,
    identifier_type: str,
    identifier_value: str,
) -> bool:
    stmt = select(SuppressionEntry.id).where(
        SuppressionEntry.organization_id == organization_id,
        SuppressionEntry.identifier_type == identifier_type,
        SuppressionEntry.identifier_value == _normalize(identifier_type, identifier_value),
    )
    return (await session.execute(stmt)).first() is not None


async def add(
    session: AsyncSession,
    *,
    organization_id: str,
    identifier_type: str,
    identifier_value: str,
    reason: str,
    source_channel: str | None = None,
    notes: str | None = None,
) -> SuppressionEntry:
    value = _normalize(identifier_type, identifier_value)
    row = SuppressionEntry(
        organization_id=organization_id,
        identifier_type=identifier_type,
        identifier_value=value,
        reason=reason,
        source_channel=source_channel,
        notes=notes,
    )
    session.add(row)
    await session.flush()
    await session.commit()
    return row


async def bulk_add(
    session: AsyncSession,
    *,
    organization_id: str,
    entries: list[tuple[str, str, str]],  # (identifier_type, value, reason)
    source_channel: str | None = None,
) -> int:
    """Bulk insert with ON CONFLICT DO NOTHING. Returns rows inserted."""
    if not entries:
        return 0
    import uuid as _uuid

    values_clauses = []
    params: dict[str, str | None] = {"org": organization_id, "src": source_channel}
    for i, (it, val, reason) in enumerate(entries):
        params[f"id{i}"] = str(_uuid.uuid4())
        params[f"it{i}"] = it
        params[f"v{i}"] = _normalize(it, val)
        params[f"r{i}"] = reason
        values_clauses.append(
            f"(:id{i}, :org, :it{i}, :v{i}, :r{i}, :src, now())"
        )
    sql = (
        "INSERT INTO suppression.entries "
        "(id, organization_id, identifier_type, identifier_value, reason, source_channel, created_at) "
        f"VALUES {','.join(values_clauses)} "
        "ON CONFLICT (organization_id, identifier_type, identifier_value) DO NOTHING"
    )
    result = await session.execute(sql_text(sql).bindparams(**params))
    await session.commit()
    return result.rowcount or 0


async def remove(
    session: AsyncSession, *, organization_id: str, entry_id: str
) -> bool:
    row = await session.get(SuppressionEntry, entry_id)
    if row is None or row.organization_id != organization_id:
        return False
    await session.delete(row)
    await session.commit()
    return True


async def list_entries(
    session: AsyncSession,
    *,
    organization_id: str,
    identifier_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[SuppressionEntry]:
    stmt = (
        select(SuppressionEntry)
        .where(SuppressionEntry.organization_id == organization_id)
        .order_by(SuppressionEntry.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if identifier_type:
        stmt = stmt.where(SuppressionEntry.identifier_type == identifier_type)
    return list((await session.execute(stmt)).scalars().all())

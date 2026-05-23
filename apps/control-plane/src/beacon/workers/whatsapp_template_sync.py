"""Background job — sync WhatsApp templates from CONNECT (which mirrors Meta).

Runs every 15min. Updates `beacon.templates` channel_kind='whatsapp' rows
with the approved templates set per org.
"""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select, text as sql_text

from beacon.db.models import Organization
from beacon.db.session import worker_session
from beacon.integrations.connect import ConnectClient, ConnectError


async def sync_once() -> int:
    updated = 0
    async with worker_session() as session:
        orgs = list((await session.execute(select(Organization))).scalars().all())
    client = ConnectClient()
    for org in orgs:
        try:
            templates = await client.list_templates(org.id)
        except ConnectError as exc:
            logging.warning("connect templates fetch failed org=%s err=%s", org.id, exc)
            continue
        async with worker_session() as session:
            for t in templates:
                slug = t.get("name", "")
                if not slug:
                    continue
                await session.execute(sql_text(
                    "INSERT INTO beacon.templates (id, tenant_id, slug, channel_kind, body_source, version, created_at) "
                    "VALUES (gen_random_uuid(), :org, :slug, 'whatsapp', :body, 1, now()) "
                    "ON CONFLICT DO NOTHING"
                ).bindparams(org=org.id, slug=slug, body=t.get("body", "")))
                updated += 1
            await session.commit()
    return updated


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    print(f"whatsapp_template_sync: updated {asyncio.run(sync_once())} rows")

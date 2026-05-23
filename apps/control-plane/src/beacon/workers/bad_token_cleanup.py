"""Background job — sweep recent deliveries for `bad_token` status and add
to suppression list if not yet present. Idempotent.

Schedule: every 15min via Kubernetes CronJob or `python -m beacon.workers.bad_token_cleanup`.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import text as sql_text

from beacon.db.session import worker_session


async def run_once(*, lookback_minutes: int = 60) -> int:
    cutoff = datetime.now(UTC) - timedelta(minutes=lookback_minutes)
    added = 0
    async with worker_session() as session:
        rows = (await session.execute(
            sql_text(
                "SELECT d.id, n.tenant_id, n.channel_kind, n.recipient "
                "FROM beacon.deliveries d JOIN beacon.notifications n ON n.id = d.notification_id "
                "WHERE d.status = 'bad_token' AND d.last_attempt_at >= :c"
            ).bindparams(c=cutoff)
        )).all()
        for _, org_id, channel, recipient in rows:
            it = "push_token" if channel.startswith("push") else "email" if channel == "email" else "phone_e164"
            try:
                await session.execute(
                    sql_text(
                        "INSERT INTO suppression.entries "
                        "(id, organization_id, identifier_type, identifier_value, reason, source_channel, created_at) "
                        "VALUES (gen_random_uuid(), :o, :it, :v, 'invalid', :ch, now()) "
                        "ON CONFLICT (organization_id, identifier_type, identifier_value) DO NOTHING"
                    ).bindparams(o=org_id, it=it, v=recipient, ch=channel)
                )
                added += 1
            except Exception as exc:  # noqa: BLE001
                logging.warning("bad_token_cleanup_failed id=%s err=%s", recipient, exc)
        await session.commit()
    return added


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    added = asyncio.run(run_once())
    print(f"bad_token_cleanup: added {added} suppression entries")

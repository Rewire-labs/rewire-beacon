"""Usage reporter — every 5min, aggregate deliveries and emit Lago events.

Metrics emitted to Lago per (organization, period):
- emails_count
- sms_count
- push_count
- whatsapp_count
- dedicated_ip_count (snapshot)
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text as sql_text

from beacon.db.session import worker_session
from beacon.integrations.lago import LagoClient, LagoError

logger = logging.getLogger(__name__)


CHANNEL_TO_METRIC = {
    "email": "emails_count",
    "sms": "sms_count",
    "push_ios": "push_count",
    "push_android": "push_count",
    "push_web": "push_count",
    "whatsapp": "whatsapp_count",
}


async def report_once(window_minutes: int = 5) -> int:
    """Aggregate deliveries in the last `window_minutes` and emit Lago events.

    Returns number of events emitted. Idempotent via transaction_id deterministic key.
    """
    end = datetime.now(UTC)
    start = end - timedelta(minutes=window_minutes)
    emitted = 0
    client = LagoClient()
    async with worker_session() as session:
        rows = (await session.execute(sql_text(
            "SELECT n.tenant_id AS org, n.channel_kind, count(*) AS cnt "
            "FROM beacon.deliveries d JOIN beacon.notifications n ON n.id = d.notification_id "
            "WHERE d.status IN ('sent','delivered','queued') AND d.created_at >= :s AND d.created_at < :e "
            "GROUP BY n.tenant_id, n.channel_kind"
        ).bindparams(s=start, e=end))).all()
    for org_id, channel, cnt in rows:
        metric = CHANNEL_TO_METRIC.get(channel)
        if not metric:
            continue
        txid = f"beacon-{org_id}-{metric}-{int(start.timestamp())}"
        try:
            await client.emit_event(
                organization_id=org_id, code=metric, transaction_id=txid,
                timestamp=end, properties={"count": int(cnt), "window_min": window_minutes},
            )
            emitted += 1
        except LagoError as exc:
            logger.warning("lago.emit_failed org=%s metric=%s err=%s", org_id, metric, exc)
    return emitted


async def _main_loop(interval_seconds: int = 300) -> None:
    while True:
        try:
            n = await report_once()
            logger.info("usage_reporter.tick emitted=%s", n)
        except Exception as exc:  # noqa: BLE001
            logger.exception("usage_reporter.tick_failed err=%s", exc)
        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main_loop())

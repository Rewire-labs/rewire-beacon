"""Analytics endpoints reading from ClickHouse (cached 5min in Redis).

- GET /v1/analytics/messages?from=...&to=...&channel=...
- GET /v1/messages/{id}/events
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from beacon.integrations.clickhouse import ClickHouseClient, ClickHouseError
from beacon.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _require_org(request: Request) -> str:
    org_id = getattr(request.state, "organization_id", None)
    if not org_id:
        raise HTTPException(status_code=400, detail="organization_required")
    return org_id


async def _redis_cache_get(key: str) -> str | None:
    try:
        from redis.asyncio import Redis  # type: ignore

        s = get_settings()
        r = Redis.from_url(s.redis_url, decode_responses=True)
        try:
            return await r.get(key)
        finally:
            await r.aclose()
    except Exception:  # noqa: BLE001
        return None


async def _redis_cache_set(key: str, value: str, ttl: int) -> None:
    try:
        from redis.asyncio import Redis  # type: ignore

        s = get_settings()
        r = Redis.from_url(s.redis_url, decode_responses=True)
        try:
            await r.set(key, value, ex=ttl)
        finally:
            await r.aclose()
    except Exception:  # noqa: BLE001
        pass


@router.get("/messages")
async def messages_summary(
    request: Request,
    from_: date = Query(default_factory=lambda: date.today() - timedelta(days=30), alias="from"),
    to: date = Query(default_factory=date.today),
    channel: str | None = Query(None),
) -> dict[str, Any]:
    org_id = _require_org(request)
    cache_key = f"beacon:analytics:msgs:{org_id}:{from_}:{to}:{channel or 'all'}"
    cached = await _redis_cache_get(cache_key)
    if cached:
        return json.loads(cached)

    where = "organization_id = {org:String} AND day BETWEEN {from:Date} AND {to:Date}"
    params: dict[str, Any] = {"org": org_id, "from": from_.isoformat(), "to": to.isoformat()}
    if channel:
        where += " AND channel = {ch:String}"
        params["ch"] = channel

    sql = (
        f"SELECT day, channel, event_type, sum(events) AS count "
        f"FROM beacon_events.daily_stats_by_org_channel WHERE {where} "
        f"GROUP BY day, channel, event_type ORDER BY day DESC, channel, event_type"
    )

    try:
        client = ClickHouseClient()
        result = await client.query(sql, params=params)
        body = {
            "from": from_.isoformat(),
            "to": to.isoformat(),
            "channel": channel,
            "rows": result.rows,
        }
    except ClickHouseError as exc:
        logger.warning("clickhouse unavailable, returning empty: %s", exc)
        body = {
            "from": from_.isoformat(), "to": to.isoformat(), "channel": channel,
            "rows": [], "warning": "clickhouse_unavailable",
        }

    await _redis_cache_set(cache_key, json.dumps(body, default=str), ttl=300)
    return body


@router.get("/messages/{message_id}/events")
async def message_events_timeline(message_id: str, request: Request) -> dict[str, Any]:
    org_id = _require_org(request)
    sql = (
        "SELECT event_at, event_type, metadata FROM beacon_events.message_events "
        "WHERE organization_id = {org:String} AND message_id = {mid:String} "
        "ORDER BY event_at ASC"
    )
    try:
        client = ClickHouseClient()
        result = await client.query(sql, params={"org": org_id, "mid": message_id})
        return {"message_id": message_id, "events": result.rows}
    except ClickHouseError as exc:
        logger.warning("clickhouse unavailable: %s", exc)
        return {"message_id": message_id, "events": [], "warning": "clickhouse_unavailable"}

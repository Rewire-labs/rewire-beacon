"""ClickHouse client wrapper (HTTP interface).

Reads `beacon_events.*` tables for analytics endpoints. Writes are
performed by ClickHouse Kafka engine consuming `beacon.events.*` topics
(no direct INSERT from API).
"""
from __future__ import annotations

import dataclasses
from typing import Any

import httpx

from beacon.settings import get_settings


@dataclasses.dataclass(slots=True)
class ClickHouseResult:
    rows: list[dict[str, Any]]


class ClickHouseError(RuntimeError):
    pass


class ClickHouseClient:
    def __init__(self, *, base_url: str | None = None, database: str = "beacon_events", timeout: float = 10.0) -> None:
        s = get_settings()
        self.base_url = (base_url or s.clickhouse_url).rstrip("/")
        self.database = database
        self._timeout = timeout

    async def query(self, sql: str, *, params: dict[str, Any] | None = None) -> ClickHouseResult:
        full_sql = sql + " FORMAT JSON" if "FORMAT" not in sql.upper() else sql
        q_params = {f"param_{k}": str(v) for k, v in (params or {}).items()}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                self.base_url + "/",
                params={"database": self.database, **q_params},
                content=full_sql.encode(),
            )
        if resp.status_code >= 400:
            raise ClickHouseError(f"clickhouse query failed [{resp.status_code}]: {resp.text}")
        data = resp.json() if resp.text and resp.text.startswith("{") else {"data": []}
        return ClickHouseResult(rows=data.get("data", []))


__all__ = ["ClickHouseClient", "ClickHouseError", "ClickHouseResult"]

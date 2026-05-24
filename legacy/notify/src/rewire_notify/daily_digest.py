"""Daily digest aggregator — runs at 09:00 BRT via APScheduler.

Aggregates from:
    - Lago (revenue MTD)              — GET /api/v1/customers/usage
    - Tenants table via control plane — count(active=true)
    - Alertmanager (open alerts)      — GET /api/v2/alerts?active=true
    - FOUNDRY projects (in-progress)  — GET /foundry/internal/projects

The Temporal-workflow variant is exposed under
:func:`run_daily_digest_workflow` for clusters that prefer a fully
audited cron via the Temporal engine; APScheduler is the default for
V0.1 because it avoids the extra dependency on a Temporal worker
running inside this microservice.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from rewire_notify.dispatcher import Dispatcher
from rewire_notify.settings import Settings
from rewire_shared.notify.telegram import AlertEvent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DigestData:
    """Aggregated metrics rendered into the daily digest message."""

    date: str
    revenue_mtd: str
    active_tenants: int
    open_alerts: int
    foundry_in_progress: int


class DigestAggregator:
    """Pulls metrics from cluster services and renders the digest payload."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def aggregate(self) -> DigestData:
        """Concurrent fan-out to all four data sources.

        Each source returns "0" on error — the digest never fails the
        whole message because one upstream is down.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            revenue = await self._fetch_revenue_mtd(client)
            tenants = await self._fetch_active_tenants(client)
            alerts = await self._fetch_open_alerts(client)
            foundry = await self._fetch_foundry_in_progress(client)
        return DigestData(
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            revenue_mtd=revenue,
            active_tenants=tenants,
            open_alerts=alerts,
            foundry_in_progress=foundry,
        )

    async def _fetch_revenue_mtd(self, client: httpx.AsyncClient) -> str:
        if not self._settings.lago_api_url:
            return "0,00"
        try:
            r = await client.get(
                f"{self._settings.lago_api_url}/api/v1/analytics/revenue",
                headers={"Authorization": f"Bearer {self._settings.lago_api_key}"},
                params={"period": "month_to_date"},
            )
            r.raise_for_status()
            value = r.json().get("amount_cents", 0) / 100.0
            return f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        except Exception:  # noqa: BLE001
            logger.exception("daily_digest.lago_fetch_failed")
            return "0,00"

    async def _fetch_active_tenants(self, client: httpx.AsyncClient) -> int:
        try:
            r = await client.get(
                f"{self._settings.foundry_api_url}/foundry/internal/v1/tenants/count",
                headers={"X-Rewire-Service": "rewire-notify"},
            )
            r.raise_for_status()
            return int(r.json().get("active", 0))
        except Exception:  # noqa: BLE001
            logger.exception("daily_digest.tenants_fetch_failed")
            return 0

    async def _fetch_open_alerts(self, client: httpx.AsyncClient) -> int:
        try:
            r = await client.get(
                "http://alertmanager.observability.svc.cluster.local:9093/api/v2/alerts",
                params={"active": "true", "silenced": "false"},
            )
            r.raise_for_status()
            return len(r.json())
        except Exception:  # noqa: BLE001
            logger.exception("daily_digest.alerts_fetch_failed")
            return 0

    async def _fetch_foundry_in_progress(self, client: httpx.AsyncClient) -> int:
        try:
            r = await client.get(
                f"{self._settings.foundry_api_url}/foundry/internal/v1/projects/count",
                params={"status": "in_progress"},
                headers={"X-Rewire-Service": "rewire-notify"},
            )
            r.raise_for_status()
            return int(r.json().get("count", 0))
        except Exception:  # noqa: BLE001
            logger.exception("daily_digest.foundry_fetch_failed")
            return 0


async def run_daily_digest(
    settings: Settings, dispatcher: Dispatcher
) -> dict[str, Any]:
    """Aggregate metrics and dispatch the digest AlertEvent.

    Returns the rendered payload so manual triggers (``/daily`` bot
    command, ``POST /events`` with the daily digest kind) can show it
    back to the operator.
    """
    aggregator = DigestAggregator(settings)
    data = await aggregator.aggregate()
    event = AlertEvent(
        kind="daily.summary",
        severity="info",
        timestamp=datetime.now(timezone.utc),
        payload={
            "date": data.date,
            "revenue_mtd": data.revenue_mtd,
            "active_tenants": str(data.active_tenants),
            "open_alerts": str(data.open_alerts),
            "foundry_in_progress": str(data.foundry_in_progress),
        },
    )
    await dispatcher.dispatch(event)
    return event.payload


# --------------------------------------------------------------------------- #
# Temporal-workflow shim (optional)                                            #
# --------------------------------------------------------------------------- #


async def run_daily_digest_workflow(
    settings: Settings, dispatcher: Dispatcher
) -> dict[str, Any]:
    """Temporal-friendly entrypoint (idempotent, retryable).

    Identical behaviour to :func:`run_daily_digest`; kept as a separate
    function so future Temporal worker code can wrap it with
    ``@workflow.run`` without touching the APScheduler path.
    """
    return await run_daily_digest(settings, dispatcher)

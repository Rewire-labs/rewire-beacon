"""FastAPI entrypoint — wires lifespan + routes + background tasks."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from rewire_notify.api import router as api_router
from rewire_notify.daily_digest import run_daily_digest
from rewire_notify.dispatcher import Dispatcher
from rewire_notify.kafka_consumer import KafkaConsumerTask
from rewire_notify.settings import get_settings
from rewire_shared.notify.telegram import (
    BotCommandCallbacks,
    BotCommandPoller,
    TelegramAdapter,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Build adapter + dispatcher; start consumer + bot poller + cron."""
    s = get_settings()
    logging.basicConfig(level=getattr(logging, s.log_level.upper(), logging.INFO))
    logger.info(
        "rewire_notify.start",
        extra={"service": s.service_name, "env": s.environment},
    )

    adapter = TelegramAdapter(
        bot_token=s.bot_token,
        default_chat_id=s.chat_id_group,
        private_chat_id=s.chat_id_private,
        group_chat_id=s.chat_id_group,
    )
    dispatcher = Dispatcher(adapter)
    app.state.adapter = adapter
    app.state.dispatcher = dispatcher

    # ---- Kafka consumer -------------------------------------------- #
    kafka_task: KafkaConsumerTask | None = None
    if s.enable_kafka_consumer:
        kafka_task = KafkaConsumerTask(s, dispatcher)
        await kafka_task.start()
    app.state.kafka_task = kafka_task

    # ---- Bot poller ------------------------------------------------ #
    poller: BotCommandPoller | None = None
    poller_task = None
    if s.enable_bot_poller and s.bot_token:
        import asyncio

        async def status_fn() -> dict[str, Any]:
            # V0.1 stub — returns 18 product entries marked healthy.
            # V0.2 will hit each product's /healthz via Kubernetes API.
            products = [
                "citadel-cloud",
                "pulse-cloud",
                "dbaas-br",
                "cloudx",
                "audit-trail",
                "host",
                "foundry",
                "rewire-app",
                "rewire-admin",
                "rewire-mcp",
                "rewire-data",
                "rewire-deploy",
            ]
            return dict.fromkeys(products, "healthy")

        async def daily_fn() -> str:
            payload = await run_daily_digest(s, dispatcher)
            return str(payload.get("date", ""))

        async def open_alerts_fn() -> list[dict[str, Any]]:
            return []

        callbacks = BotCommandCallbacks(
            status_fn=status_fn,
            daily_digest_fn=daily_fn,
            open_alerts_fn=open_alerts_fn,
        )
        poller = BotCommandPoller(
            adapter=adapter,
            callbacks=callbacks,
            allowed_chat_ids={s.chat_id_private, s.chat_id_group},
            poll_timeout=s.bot_poll_timeout_seconds,
        )
        poller_task = asyncio.create_task(poller.run(), name="rewire-notify.bot_poller")
    app.state.bot_poller = poller
    app.state.bot_poller_task = poller_task

    # ---- Daily digest cron ----------------------------------------- #
    scheduler: AsyncIOScheduler | None = None
    if s.enable_daily_digest:
        scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")
        scheduler.add_job(
            run_daily_digest,
            trigger=CronTrigger(
                hour=s.daily_digest_cron_hour_brt,
                minute=s.daily_digest_cron_minute_brt,
            ),
            args=[s, dispatcher],
            id="daily_digest",
            replace_existing=True,
        )
        scheduler.start()
    app.state.scheduler = scheduler

    # Dev seed — popula tenant/user dev pra smoke `auth200`. Opt-in via
    # REWIRE_NOTIFY_SEED_DEV_DATA=true; gated por ENVIRONMENT=dev.
    try:
        from rewire_notify.dev_seed import is_seed_enabled, seed_dev_data

        if is_seed_enabled():
            await seed_dev_data()
    except Exception as exc:  # noqa: BLE001 — never crash dev cold start
        logger.warning("dev.seed.failed: %s", exc)

    logger.info("rewire_notify.ready")
    try:
        yield
    finally:
        logger.info("rewire_notify.shutdown")
        if scheduler is not None:
            scheduler.shutdown(wait=False)
        if poller is not None:
            poller.stop()
        if poller_task is not None:
            try:
                await poller_task
            except Exception:  # noqa: BLE001
                pass
        if kafka_task is not None:
            await kafka_task.stop()
        await adapter.aclose()


def create_app() -> FastAPI:
    """FastAPI factory used by uvicorn and tests."""
    app = FastAPI(
        title="rewire-notify",
        version="0.1.0",
        description="Rewire internal notification dispatcher (Telegram).",
        lifespan=lifespan,
    )
    app.include_router(api_router)

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> PlainTextResponse:
        return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    s = get_settings()
    uvicorn.run(
        "rewire_notify.main:app",
        host=s.http_host,
        port=s.http_port,
        log_level=s.log_level.lower(),
    )

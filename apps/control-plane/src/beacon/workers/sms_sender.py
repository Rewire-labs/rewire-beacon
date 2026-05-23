"""SMS Kafka consumer — Zenvia primary, TotalVoice fallback.

Per BCN-052: BSP routing decision per `providers.sms_provider_routes`.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
from datetime import UTC, datetime
from typing import Any

import structlog

from beacon.integrations.totalvoice import TotalVoiceClient, TotalVoiceError
from beacon.integrations.zenvia import ZenviaClient, ZenviaError
from beacon.settings import get_settings

logger = structlog.get_logger(__name__)


class SmsSenderWorker:
    def __init__(self, *, tier: str = "starter") -> None:
        self.tier = tier
        self.topic = f"beacon.send.sms.{tier}"
        self.group_id = f"beacon-sms-sender-{tier}"
        self._zenvia = ZenviaClient()
        self._totalvoice = TotalVoiceClient()
        self._running = True

    async def _consume(self) -> None:
        try:
            from aiokafka import AIOKafkaConsumer  # type: ignore
        except ImportError:
            logger.warning("aiokafka not installed — sms worker idle in dev")
            while self._running:
                await asyncio.sleep(1)
            return
        s = get_settings()
        consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=s.kafka_brokers,
            group_id=self.group_id,
            value_deserializer=lambda b: json.loads(b.decode("utf-8")),
            enable_auto_commit=False,
        )
        await consumer.start()
        logger.info("sms_sender.started", topic=self.topic)
        try:
            async for msg in consumer:
                if not self._running:
                    break
                try:
                    await self._handle(msg.value)
                    await consumer.commit()
                except Exception as exc:  # noqa: BLE001
                    logger.exception("sms_sender.handle_failed", error=str(exc))
        finally:
            await consumer.stop()

    async def _handle(self, env: dict[str, Any]) -> None:
        message_id = env.get("message_id", "unknown")
        to = env["to"]
        text = env["text"]
        from_number = env.get("from_number", "BEACON")

        provider = "zenvia"
        msg_id: str = ""
        status: str = "failed"
        cost_cents = 0
        error: str | None = None

        try:
            r = await self._zenvia.send_sms(from_number=from_number, to=to, text=text)
            msg_id, status, cost_cents = r.message_id, r.status, r.cost_brl_cents
        except ZenviaError as exc:
            logger.warning("zenvia.failed", message_id=message_id, error=str(exc))
            try:
                r2 = await self._totalvoice.send_sms(to=to, text=text)
                provider, msg_id, status, cost_cents = "totalvoice", r2.message_id, r2.status, r2.cost_brl_cents
            except TotalVoiceError as exc2:
                error = f"zenvia+totalvoice failed: {exc}; {exc2}"

        await self._record(
            message_id=message_id, provider=provider, msg_id=msg_id,
            status=status, error=error, cost_cents=cost_cents,
        )

    async def _record(
        self,
        *,
        message_id: str,
        provider: str,
        msg_id: str,
        status: str,
        error: str | None,
        cost_cents: int,
    ) -> None:
        try:
            from sqlalchemy import text as sql_text

            from beacon.db.session import worker_session

            async with worker_session() as session:
                await session.execute(
                    sql_text(
                        "UPDATE beacon.deliveries SET provider = :p, provider_message_id = :pm, "
                        "status = :st, error_message = :em, attempts = attempts + 1, "
                        "last_attempt_at = :ts WHERE notification_id = :nid"
                    ).bindparams(
                        p=provider, pm=msg_id, st=status, em=error,
                        ts=datetime.now(UTC), nid=message_id,
                    )
                )
                await session.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning("sms_delivery_record_failed", error=str(exc))

    def stop(self) -> None:
        self._running = False


async def _main() -> None:
    tier = os.environ.get("BEACON_WORKER_TIER", "starter")
    logging.basicConfig(level=logging.INFO)
    w = SmsSenderWorker(tier=tier)
    loop = asyncio.get_running_loop()
    for sig in ("SIGINT", "SIGTERM"):
        try:
            loop.add_signal_handler(getattr(signal, sig), w.stop)
        except (NotImplementedError, AttributeError):
            pass
    await w._consume()


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(_main())

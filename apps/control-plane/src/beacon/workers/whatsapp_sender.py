"""WhatsApp worker — delegates to CONNECT internal API.

Per BCN-081: BEACON owns enqueue + chain hash + suppression; CONNECT owns
Meta WhatsApp protocol details and BSP routing.
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

from beacon.integrations.connect import ConnectClient, ConnectError
from beacon.settings import get_settings

logger = structlog.get_logger(__name__)


class WhatsAppSenderWorker:
    def __init__(self, *, tier: str = "starter") -> None:
        self.tier = tier
        self.topic = f"beacon.send.whatsapp.{tier}"
        self.group_id = f"beacon-whatsapp-sender-{tier}"
        self._connect = ConnectClient()
        self._running = True

    async def _consume(self) -> None:
        try:
            from aiokafka import AIOKafkaConsumer  # type: ignore
        except ImportError:
            logger.warning("aiokafka not installed — whatsapp worker idle")
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
        logger.info("whatsapp_sender.started", topic=self.topic)
        try:
            async for msg in consumer:
                if not self._running:
                    break
                try:
                    await self._handle(msg.value)
                    await consumer.commit()
                except Exception as exc:  # noqa: BLE001
                    logger.exception("whatsapp_sender.handle_failed", error=str(exc))
        finally:
            await consumer.stop()

    async def _handle(self, env: dict[str, Any]) -> None:
        message_id = env.get("message_id", "unknown")
        provider_msg_id = ""
        status = "failed"
        error: str | None = None
        try:
            r = await self._connect.send_whatsapp(
                organization_id=env["organization_id"],
                to=env["to"],
                template_name=env["template_name"],
                template_vars=env.get("template_vars"),
                body_text=env.get("body_text"),
            )
            provider_msg_id, status = r.message_id, r.status
        except ConnectError as exc:
            error = str(exc)
        await self._record(message_id, provider_msg_id, status, error)

    async def _record(self, message_id: str, msg_id: str, status: str, error: str | None) -> None:
        try:
            from sqlalchemy import text as sql_text

            from beacon.db.session import worker_session

            async with worker_session() as session:
                await session.execute(
                    sql_text(
                        "UPDATE beacon.deliveries SET provider = 'connect', provider_message_id = :pm, "
                        "status = :st, error_message = :em, attempts = attempts + 1, "
                        "last_attempt_at = :ts WHERE notification_id = :nid"
                    ).bindparams(pm=msg_id, st=status, em=error, ts=datetime.now(UTC), nid=message_id)
                )
                await session.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning("whatsapp_record_failed", error=str(exc))

    def stop(self) -> None:
        self._running = False


async def _main() -> None:
    tier = os.environ.get("BEACON_WORKER_TIER", "starter")
    logging.basicConfig(level=logging.INFO)
    w = WhatsAppSenderWorker(tier=tier)
    loop = asyncio.get_running_loop()
    for sig in ("SIGINT", "SIGTERM"):
        try:
            loop.add_signal_handler(getattr(signal, sig), w.stop)
        except (NotImplementedError, AttributeError):
            pass
    await w._consume()


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(_main())

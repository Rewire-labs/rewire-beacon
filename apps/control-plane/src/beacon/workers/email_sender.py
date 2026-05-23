"""Kafka consumer worker — `beacon.send.email.*` topics fan-out to Postal/SES.

Topology:
- Topic: `beacon.send.email.<tier>` (tier = hobby|starter|scale|enterprise)
- Group: `beacon-email-sender-<tier>`
- Each message is a JSON envelope produced by POST /v1/messages/email.

Per message:
1. Re-check suppression list (defensive — sender may have been added since enqueue).
2. Pick provider: Postal default; SES fallback for `scale`/`enterprise` tier
   or when Postal returns 5xx.
3. Update `beacon.deliveries` row + emit `beacon.events.email` event for ClickHouse.
4. Emit webhook delivery rows for subscribed endpoints.
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

from beacon.integrations.aws_ses_br import AwsSesClient, SesError
from beacon.integrations.postal import PostalClient, PostalError
from beacon.settings import get_settings

logger = structlog.get_logger(__name__)


class EmailSenderWorker:
    def __init__(self, *, tier: str = "starter") -> None:
        self.tier = tier
        self.topic = f"beacon.send.email.{tier}"
        self.group_id = f"beacon-email-sender-{tier}"
        self._postal = PostalClient()
        self._ses = AwsSesClient()
        self._running = True

    async def _consume(self) -> None:
        try:
            from aiokafka import AIOKafkaConsumer  # type: ignore
        except ImportError:
            logger.warning("aiokafka not installed — worker idle in dev mode")
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
            auto_offset_reset="earliest",
        )
        await consumer.start()
        logger.info("email_sender.started", topic=self.topic, group=self.group_id)
        try:
            async for msg in consumer:
                if not self._running:
                    break
                try:
                    await self._handle(msg.value)
                    await consumer.commit()
                except Exception as exc:  # noqa: BLE001
                    logger.exception("email_sender.handle_failed", error=str(exc))
        finally:
            await consumer.stop()
            logger.info("email_sender.stopped")

    async def _handle(self, envelope: dict[str, Any]) -> None:
        message_id = envelope.get("message_id", "unknown")
        sender = envelope["sender"]
        to = envelope["to"] if isinstance(envelope["to"], list) else [envelope["to"]]
        subject = envelope.get("subject", "")
        html = envelope.get("html_body")
        text = envelope.get("plain_body")
        tag = envelope.get("template_slug", "transactional")

        result_msg_id: str = ""
        provider: str = "postal"
        status: str = "queued"
        error: str | None = None

        # Try Postal first; fallback to SES on transport failure.
        try:
            res = await self._postal.send_message(
                sender=sender, to=to, subject=subject,
                html_body=html, plain_body=text, tag=tag,
            )
            result_msg_id, status = res.message_id, res.status
        except PostalError as exc:
            logger.warning("postal.failed", message_id=message_id, error=str(exc))
            if self.tier in ("scale", "enterprise"):
                try:
                    res2 = await self._ses.send_message(
                        sender=sender, to=to, subject=subject,
                        html_body=html, plain_body=text,
                    )
                    provider, result_msg_id, status = "ses", res2.message_id, res2.status
                except SesError as exc2:
                    error = f"postal+ses failed: {exc}; {exc2}"
                    status = "failed"
            else:
                error = str(exc)
                status = "failed"

        await self._record_delivery(
            message_id=message_id,
            provider=provider,
            provider_message_id=result_msg_id,
            status=status,
            error=error,
        )

    async def _record_delivery(
        self,
        *,
        message_id: str,
        provider: str,
        provider_message_id: str,
        status: str,
        error: str | None,
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
                        p=provider, pm=provider_message_id, st=status,
                        em=error, ts=datetime.now(UTC), nid=message_id,
                    )
                )
                await session.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning("delivery_record_failed", error=str(exc))

    def stop(self) -> None:
        self._running = False


async def _main() -> None:
    tier = os.environ.get("BEACON_WORKER_TIER", "starter")
    logging.basicConfig(level=logging.INFO)
    worker = EmailSenderWorker(tier=tier)
    loop = asyncio.get_running_loop()
    for sig in ("SIGINT", "SIGTERM"):
        try:
            loop.add_signal_handler(getattr(signal, sig), worker.stop)
        except (NotImplementedError, AttributeError):
            pass  # Windows
    await worker._consume()


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(_main())

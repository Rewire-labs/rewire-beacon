"""Push mobile worker — fans out to APNs / FCM based on platform.

Topology:
- Topic: `beacon.send.push.{ios|android|web}.{tier}`
- Group: `beacon-push-sender-{platform}-{tier}`
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

from beacon.integrations.apns import ApnsClient, ApnsError
from beacon.integrations.fcm import FcmClient, FcmError
from beacon.integrations.webpush import WebPushClient, WebPushError
from beacon.settings import get_settings

logger = structlog.get_logger(__name__)


class PushSenderWorker:
    def __init__(self, *, platform: str = "android", tier: str = "starter") -> None:
        self.platform = platform
        self.tier = tier
        self.topic = f"beacon.send.push.{platform}.{tier}"
        self.group_id = f"beacon-push-sender-{platform}-{tier}"
        self._running = True

    async def _consume(self) -> None:
        try:
            from aiokafka import AIOKafkaConsumer  # type: ignore
        except ImportError:
            logger.warning("aiokafka not installed — push worker idle")
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
        logger.info("push_sender.started", topic=self.topic)
        try:
            async for msg in consumer:
                if not self._running:
                    break
                try:
                    await self._handle(msg.value)
                    await consumer.commit()
                except Exception as exc:  # noqa: BLE001
                    logger.exception("push_sender.handle_failed", error=str(exc))
        finally:
            await consumer.stop()

    async def _handle(self, env: dict[str, Any]) -> None:
        message_id = env.get("message_id", "unknown")
        token = env["device_token"]
        title = env["title"]
        body = env["body"]
        data = env.get("data") or {}

        provider = ""
        status = "failed"
        provider_msg_id = ""
        error: str | None = None

        try:
            if self.platform == "ios":
                client = ApnsClient(p8_pem=os.environ.get("BEACON_APNS_P8_PEM"))
                r = await client.send(device_token=token, title=title, body=body, data=data)
                provider, provider_msg_id, status = "apns", r.apns_id, r.status
            elif self.platform == "android":
                client = FcmClient(service_account_json=os.environ.get("BEACON_FCM_SA_JSON"))
                r = await client.send(device_token=token, title=title, body=body, data=data)
                provider, provider_msg_id, status = "fcm", r.message_name, r.status
            elif self.platform == "web":
                # web token here is actually the full subscription JSON.
                sub = json.loads(token) if token.startswith("{") else {"endpoint": token, "keys": {}}
                client = WebPushClient()
                r = await client.send(subscription=sub, title=title, body=body, data=data)
                provider, status = "webpush", r.status
        except (ApnsError, FcmError, WebPushError) as exc:
            error = str(exc)

        # bad_token -> auto-suppression
        if status == "bad_token":
            try:
                from beacon.db.session import worker_session
                from beacon.services import suppression as svc

                org_id = env["organization_id"]
                async with worker_session() as session:
                    await svc.add(
                        session, organization_id=org_id,
                        identifier_type="push_token", identifier_value=token,
                        reason="invalid", source_channel=f"push_{self.platform}",
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning("bad_token_suppress_failed", error=str(exc))

        await self._record(
            message_id=message_id, provider=provider, msg_id=provider_msg_id,
            status=status, error=error,
        )

    async def _record(self, *, message_id: str, provider: str, msg_id: str, status: str, error: str | None) -> None:
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
            logger.warning("push_delivery_record_failed", error=str(exc))

    def stop(self) -> None:
        self._running = False


async def _main() -> None:
    platform = os.environ.get("BEACON_PUSH_PLATFORM", "android")
    tier = os.environ.get("BEACON_WORKER_TIER", "starter")
    logging.basicConfig(level=logging.INFO)
    w = PushSenderWorker(platform=platform, tier=tier)
    loop = asyncio.get_running_loop()
    for sig in ("SIGINT", "SIGTERM"):
        try:
            loop.add_signal_handler(getattr(signal, sig), w.stop)
        except (NotImplementedError, AttributeError):
            pass
    await w._consume()


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(_main())

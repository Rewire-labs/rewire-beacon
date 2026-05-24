"""Redpanda consumer task — drains ``cluster.events.global`` → telegram."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from rewire_notify.dispatcher import Dispatcher, event_payload_to_event
from rewire_notify.settings import Settings

logger = logging.getLogger(__name__)


class KafkaConsumerTask:
    """Async consumer task running for the lifetime of the FastAPI app."""

    def __init__(self, settings: Settings, dispatcher: Dispatcher) -> None:
        self._settings = settings
        self._dispatcher = dispatcher
        self._stop = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Launch the consumer task; idempotent."""
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._run(), name="rewire-notify.kafka")

    async def stop(self) -> None:
        """Signal stop and await graceful shutdown."""
        self._stop.set()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=10.0)
            except asyncio.TimeoutError:
                self._task.cancel()

    async def _run(self) -> None:
        """Inner loop — uses aiokafka if available, else logs and exits.

        We import aiokafka lazily so unit tests don't pay the dependency
        cost and dev compose without Redpanda still boots cleanly.
        """
        try:
            from aiokafka import AIOKafkaConsumer  # type: ignore[import-not-found]
        except ImportError:
            logger.warning(
                "kafka_consumer.aiokafka_missing — consumer disabled. "
                "Install rewire-notify[kafka] to enable."
            )
            return

        consumer = AIOKafkaConsumer(
            self._settings.kafka_topic_events,
            bootstrap_servers=self._settings.kafka_brokers,
            group_id=self._settings.kafka_consumer_group,
            enable_auto_commit=True,
            auto_offset_reset="latest",
            value_deserializer=lambda b: json.loads(b.decode("utf-8")),
        )
        await consumer.start()
        logger.info(
            "kafka_consumer.started",
            extra={
                "topic": self._settings.kafka_topic_events,
                "group": self._settings.kafka_consumer_group,
            },
        )
        try:
            async for msg in consumer:
                if self._stop.is_set():
                    break
                try:
                    payload: dict[str, Any] = msg.value
                    event = event_payload_to_event(payload)
                    await self._dispatcher.dispatch(event)
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "kafka_consumer.dispatch_error",
                        extra={"offset": msg.offset, "topic": msg.topic},
                    )
        finally:
            await consumer.stop()
            logger.info("kafka_consumer.stopped")

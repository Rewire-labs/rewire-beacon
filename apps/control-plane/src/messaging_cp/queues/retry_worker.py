"""pgmq retry worker — drains DLQ with exponential backoff.

Responsibility:
  - Read from ``messaging_outbound_dlq``.
  - If retry-eligible (``_retries < max_retries``), re-publish to original
    channel queue with ``_retries += 1`` and exponential delay.
  - Otherwise, mark message as permanently failed in ``deliveries`` table
    and archive the DLQ entry.

The retry worker is a single process; one is enough because DLQ traffic is
low and operations are idempotent.
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import time
from dataclasses import dataclass
from typing import Any

from messaging_cp.queues.sender_worker import PGMQ_DLQ, PGMQ_QUEUE

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RetryStats:
    processed: int = 0
    requeued: int = 0
    permanent_fail: int = 0


class RetryWorker:
    def __init__(
        self,
        *,
        db_pool: Any | None = None,
        poll_interval_seconds: float = 5.0,
        max_retries: int = 5,
        base_backoff_seconds: int = 60,
    ) -> None:
        self._db = db_pool
        self._poll = poll_interval_seconds
        self._max = max_retries
        self._base_backoff = base_backoff_seconds
        self._running = False
        self.stats = RetryStats()

    def _install_signal_handlers(self) -> None:
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, lambda: setattr(self, "_running", False))
            except (NotImplementedError, RuntimeError):
                pass

    async def run_forever(self) -> None:
        self._running = True
        self._install_signal_handlers()
        logger.info("messaging.retry_worker.start", extra={"queue": PGMQ_DLQ})
        while self._running:
            try:
                msg = await self._read_one()
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "messaging.retry_worker.read_failed", extra={"error": str(exc)}
                )
                await asyncio.sleep(self._poll)
                continue
            if msg is None:
                await asyncio.sleep(self._poll)
                continue
            await self._handle(msg)

    async def _read_one(self) -> dict[str, Any] | None:
        if self._db is None:
            return None
        async with self._db.acquire() as conn:  # type: ignore[union-attr]
            row = await conn.fetchrow(
                "SELECT msg_id, message FROM pgmq.read(:queue, 30, 1) LIMIT 1",
                queue=PGMQ_DLQ,
            )
        if row is None:
            return None
        payload = row["message"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        return {"msg_id": row["msg_id"], "payload": payload}

    async def _archive(self, msg_id: int) -> None:
        if self._db is None:
            return
        async with self._db.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute(
                "SELECT pgmq.archive(:queue, :msg_id)", queue=PGMQ_DLQ, msg_id=msg_id
            )

    async def _requeue(self, channel: str, payload: dict[str, Any], retries: int) -> None:
        if self._db is None:
            return
        delay_seconds = self._base_backoff * (2 ** retries)
        new_payload = dict(payload)
        new_payload["_retries"] = retries + 1
        target_queue = PGMQ_QUEUE.get(channel)
        if target_queue is None:
            self.stats.permanent_fail += 1
            return
        async with self._db.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute(
                "SELECT pgmq.send(:queue, :msg::jsonb, :delay)",
                queue=target_queue,
                msg=json.dumps(new_payload),
                delay=delay_seconds,
            )
        self.stats.requeued += 1

    async def _handle(self, envelope: dict[str, Any]) -> None:
        msg_id = envelope["msg_id"]
        payload = envelope["payload"]
        self.stats.processed += 1
        retries = int(payload.get("_retries", 0))
        channel = payload.get("_dlq_channel", "email")
        if retries >= self._max:
            logger.warning(
                "messaging.retry_worker.permanent_fail",
                extra={"channel": channel, "msg_id": msg_id, "retries": retries},
            )
            self.stats.permanent_fail += 1
            await self._archive(msg_id)
            return
        await self._requeue(channel, payload, retries)
        await self._archive(msg_id)


__all__ = ["RetryWorker", "RetryStats"]

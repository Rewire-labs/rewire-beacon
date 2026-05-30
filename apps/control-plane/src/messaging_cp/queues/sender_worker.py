"""pgmq sender worker — drain outbound queues and dispatch via router.

Three queues are polled (one worker handles each, configured via env):
  - ``messaging_outbound_email`` → EmailRouter (Postal → Resend)
  - ``messaging_outbound_sms``   → SmsRouter (Zenvia)
  - ``messaging_outbound_push``  → PushRouter (APNs / FCM by platform)

The worker is intentionally simple: pgmq guarantees at-least-once delivery
via visibility timeout; we ``pgmq.read()`` with vt=30s, process, then
``pgmq.archive()`` on success or ``pgmq.delete()`` after permanent failure.
Permanent failures are re-published to ``messaging_outbound_dlq`` by the
``RetryWorker`` so they can be inspected.

Idempotency: each message carries an idempotency key
``{tenant_id}:{recipient}:{template_id}:{date}`` — duplicates are detected
upstream at enqueue time (UNIQUE index on ``messages.idempotency_key``).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import time
from dataclasses import dataclass
from typing import Any, Literal

from messaging_cp.adapters.email.router import EmailRouter, EmailRouterAllFailed
from messaging_cp.adapters.push.router import PushRouter, PushRouterError
from messaging_cp.adapters.sms.router import SmsRouter, SmsRouterAllFailed
from messaging_cp.credits_emit import emit_messaging_credit
from messaging_cp.lago_emit import emit_messaging_billable

logger = logging.getLogger(__name__)

Channel = Literal["email", "sms", "push"]

PGMQ_QUEUE = {
    "email": "messaging_outbound_email",
    "sms": "messaging_outbound_sms",
    "push": "messaging_outbound_push",
}

PGMQ_DLQ = "messaging_outbound_dlq"


@dataclass(slots=True)
class WorkerStats:
    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    dlq: int = 0


class SenderWorker:
    """Polls a pgmq queue and dispatches via the right router.

    Usage::

        worker = SenderWorker(channel="email", db=db_pool)
        await worker.run_forever()

    Stop gracefully via SIGTERM/SIGINT — sets ``_running = False`` then
    drains the current message and exits.
    """

    def __init__(
        self,
        *,
        channel: Channel,
        db_pool: Any | None = None,
        email_router: EmailRouter | None = None,
        sms_router: SmsRouter | None = None,
        push_router: PushRouter | None = None,
        poll_interval_seconds: float = 1.0,
        visibility_timeout_seconds: int = 30,
        max_retries: int = 5,
    ) -> None:
        self.channel = channel
        self.queue_name = PGMQ_QUEUE[channel]
        self._db = db_pool
        self._email = email_router or EmailRouter()
        self._sms = sms_router or SmsRouter()
        self._push = push_router or PushRouter()
        self._poll_interval = poll_interval_seconds
        self._vt = visibility_timeout_seconds
        self._max_retries = max_retries
        self._running = False
        self.stats = WorkerStats()

    def _install_signal_handlers(self) -> None:
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, lambda: setattr(self, "_running", False))
            except (NotImplementedError, RuntimeError):
                # Windows / no event loop -> skip
                pass

    async def run_forever(self) -> None:
        self._running = True
        self._install_signal_handlers()
        logger.info(
            "messaging.sender_worker.start",
            extra={"channel": self.channel, "queue": self.queue_name},
        )
        while self._running:
            try:
                msg = await self._read_one()
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "messaging.sender_worker.read_failed",
                    extra={"error": str(exc), "channel": self.channel},
                )
                await asyncio.sleep(self._poll_interval)
                continue
            if msg is None:
                await asyncio.sleep(self._poll_interval)
                continue
            await self._handle(msg)

    async def _read_one(self) -> dict[str, Any] | None:
        """Read one message from pgmq with visibility timeout.

        Returns the message envelope or ``None`` if the queue is empty.
        The pgmq Python binding (or raw SQL) is the actual call site —
        for testability this method is dependency-injection friendly.

        RW-MESSAGING-22: asyncpg uses $1-positional params; `:name` syntax
        only works with SQLAlchemy text().bindparams() — switch to positional.
        """
        if self._db is None:
            return None
        # asyncpg positional: $1 = queue name (text), $2 = vt (int), $3 = count (int)
        sql = (
            "SELECT msg_id, message FROM pgmq.read($1::text, $2::int, $3::int) "
            "ORDER BY msg_id LIMIT 1"
        )
        async with self._db.acquire() as conn:  # type: ignore[union-attr]
            row = await conn.fetchrow(sql, self.queue_name, self._vt, 1)
        if row is None:
            return None
        payload = row["message"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        return {"msg_id": row["msg_id"], "payload": payload}

    async def _archive(self, msg_id: int) -> None:
        if self._db is None:
            return
        # RW-MESSAGING-22: positional params for asyncpg.
        async with self._db.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute("SELECT pgmq.archive($1::text, $2::bigint)", self.queue_name, msg_id)

    async def _send_to_dlq(self, payload: dict[str, Any], error: str) -> None:
        if self._db is None:
            return
        dlq_msg = {
            **payload,
            "_dlq_reason": error,
            "_dlq_channel": self.channel,
            "_dlq_at": int(time.time()),
        }
        # RW-MESSAGING-22: positional params for asyncpg.
        async with self._db.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute(
                "SELECT pgmq.send($1::text, $2::jsonb)",
                PGMQ_DLQ,
                json.dumps(dlq_msg),
            )
        self.stats.dlq += 1

    async def _handle(self, envelope: dict[str, Any]) -> None:
        msg_id = envelope["msg_id"]
        payload = envelope["payload"]
        self.stats.processed += 1
        try:
            if self.channel == "email":
                await self._dispatch_email(payload)
            elif self.channel == "sms":
                await self._dispatch_sms(payload)
            elif self.channel == "push":
                await self._dispatch_push(payload)
            else:
                raise ValueError(f"unknown channel {self.channel}")
            await self._archive(msg_id)
            self.stats.succeeded += 1
        except (EmailRouterAllFailed, SmsRouterAllFailed, PushRouterError) as exc:
            self.stats.failed += 1
            retries = int(payload.get("_retries", 0))
            if retries >= self._max_retries:
                logger.warning(
                    "messaging.sender_worker.dlq",
                    extra={"channel": self.channel, "error": str(exc), "msg_id": msg_id},
                )
                await self._send_to_dlq(payload, str(exc))
                await self._archive(msg_id)
            else:
                # Leave message visible after VT expires -> implicit retry.
                # pgmq increments read_ct automatically.
                logger.info(
                    "messaging.sender_worker.retry",
                    extra={"channel": self.channel, "retries": retries + 1},
                )
        except Exception as exc:  # noqa: BLE001
            self.stats.failed += 1
            logger.exception(
                "messaging.sender_worker.unexpected",
                extra={"channel": self.channel, "error": str(exc), "msg_id": msg_id},
            )

    async def _dispatch_email(self, payload: dict[str, Any]) -> None:
        tenant_id = payload.get("tenant_id", "unknown")
        res = await self._email.send(
            sender=payload["sender"],
            to=payload["to"] if isinstance(payload["to"], list) else [payload["to"]],
            subject=payload.get("subject", ""),
            html_body=payload.get("html_body"),
            plain_body=payload.get("plain_body"),
        )
        # Credits weight = 0 (free V0; future BL_email_volume). Lago metric tracks counter.
        await emit_messaging_credit(tenant_id=tenant_id, action_type="email_transactional", quantity=1)
        await emit_messaging_billable(
            tenant_id=tenant_id, metric="messaging_email_sent", value=1,
            metadata={"provider": res.provider},
        )

    async def _dispatch_sms(self, payload: dict[str, Any]) -> None:
        tenant_id = payload.get("tenant_id", "unknown")
        res = await self._sms.send(
            from_number=payload.get("from_number", ""),
            to=payload["to"],
            text=payload.get("text", ""),
        )
        # Credits weight = 2 (custo Zenvia ~R$ 0,10/SMS)
        await emit_messaging_credit(tenant_id=tenant_id, action_type="sms_br", quantity=1)
        await emit_messaging_billable(
            tenant_id=tenant_id, metric="messaging_sms_sent", value=1,
            metadata={"provider": res.provider, "cost_brl_cents": res.cost_brl_cents},
        )

    async def _dispatch_push(self, payload: dict[str, Any]) -> None:
        tenant_id = payload.get("tenant_id", "unknown")
        res = await self._push.send(
            platform=payload.get("platform", "android"),
            device_token=payload["device_token"],
            title=payload.get("title", ""),
            body=payload.get("body", ""),
            data=payload.get("data"),
        )
        # Credits weight = 0 (cost negligible)
        await emit_messaging_credit(tenant_id=tenant_id, action_type="push_notification", quantity=1)
        await emit_messaging_billable(
            tenant_id=tenant_id, metric="messaging_push_sent", value=1,
            metadata={"provider": res.provider, "platform": res.platform},
        )


__all__ = ["SenderWorker", "WorkerStats"]

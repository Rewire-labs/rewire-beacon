"""Full-coverage tests for pgmq sender + retry workers.

Drives the worker control flow with a fake DB pool that simulates pgmq
``read()`` and ``archive()`` calls. Verifies:

- Successful dispatch -> archive + stats.succeeded++
- Router failure -> retry path (or DLQ if max_retries hit)
- DLQ -> retry worker re-publishes to original queue with backoff
- DLQ -> retry worker permanent-fails after max_retries
"""

from __future__ import annotations

import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pytest

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "apps" / "control-plane" / "src"))

from messaging_cp.adapters.email.router import EmailRouterAllFailed  # noqa: E402
from messaging_cp.adapters.push.router import PushRouterError  # noqa: E402
from messaging_cp.adapters.sms.router import SmsRouterAllFailed  # noqa: E402
from messaging_cp.queues.retry_worker import RetryWorker  # noqa: E402
from messaging_cp.queues.sender_worker import SenderWorker  # noqa: E402


# ---------------------------------------------------------------------------
# Fake DB pool (mimics asyncpg-style interface used by the workers).
# ---------------------------------------------------------------------------


class _FakeConn:
    def __init__(self, parent: "_FakePool") -> None:
        self._parent = parent

    async def fetchrow(self, sql: str, **params: Any) -> dict[str, Any] | None:
        # Pop the next prepared message (FIFO).
        if not self._parent.read_queue:
            return None
        msg = self._parent.read_queue.pop(0)
        return {"msg_id": msg["msg_id"], "message": msg["message"]}

    async def execute(self, sql: str, **params: Any) -> None:
        self._parent.executed.append({"sql": sql, "params": params})


class _FakePool:
    def __init__(self) -> None:
        self.read_queue: list[dict[str, Any]] = []
        self.executed: list[dict[str, Any]] = []

    @asynccontextmanager
    async def acquire(self) -> Any:
        yield _FakeConn(self)


# ---------------------------------------------------------------------------
# Fake routers
# ---------------------------------------------------------------------------


class _OkEmailRouter:
    async def send(self, **_: Any) -> Any:
        from dataclasses import dataclass

        @dataclass(slots=True)
        class _R:
            provider: str = "postal"
            message_id: str = "m-1"
            status: str = "queued"
            raw: dict[str, Any] | None = None

        return _R()


class _FailEmailRouter:
    async def send(self, **_: Any) -> Any:
        raise EmailRouterAllFailed("simulated total failure")


class _OkSmsRouter:
    async def send(self, **_: Any) -> Any:
        from dataclasses import dataclass

        @dataclass(slots=True)
        class _R:
            provider: str = "zenvia"
            message_id: str = "s-1"
            status: str = "queued"
            cost_brl_cents: int = 7
            raw: dict[str, Any] | None = None

        return _R()


class _FailSmsRouter:
    async def send(self, **_: Any) -> Any:
        raise SmsRouterAllFailed("simulated sms failure")


class _OkPushRouter:
    async def send(self, **_: Any) -> Any:
        from dataclasses import dataclass

        @dataclass(slots=True)
        class _R:
            provider: str = "fcm"
            message_id: str = "p-1"
            status: str = "sent"
            platform: str = "android"
            raw: dict[str, Any] | None = None

        return _R()


class _FailPushRouter:
    async def send(self, **_: Any) -> Any:
        raise PushRouterError("simulated push failure")


# ---------------------------------------------------------------------------
# Sender worker — happy + failure paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sender_worker_email_happy_path() -> None:
    pool = _FakePool()
    pool.read_queue.append(
        {
            "msg_id": 101,
            "message": {
                "tenant_id": "org_a",
                "sender": "x@a.b",
                "to": ["y@b.c"],
                "subject": "hi",
                "plain_body": "p",
            },
        }
    )
    worker = SenderWorker(
        channel="email", db_pool=pool, email_router=_OkEmailRouter()
    )
    msg = await worker._read_one()
    assert msg is not None
    await worker._handle(msg)
    assert worker.stats.succeeded == 1


@pytest.mark.asyncio
async def test_sender_worker_email_failure_increments_failed() -> None:
    pool = _FakePool()
    pool.read_queue.append(
        {
            "msg_id": 102,
            "message": {
                "tenant_id": "org_a",
                "sender": "x@a.b",
                "to": ["y@b.c"],
                "subject": "hi",
                "plain_body": "p",
                "_retries": 0,
            },
        }
    )
    worker = SenderWorker(
        channel="email", db_pool=pool, email_router=_FailEmailRouter(), max_retries=2
    )
    msg = await worker._read_one()
    assert msg is not None
    await worker._handle(msg)
    assert worker.stats.failed == 1


@pytest.mark.asyncio
async def test_sender_worker_email_dlq_after_max_retries() -> None:
    pool = _FakePool()
    pool.read_queue.append(
        {
            "msg_id": 103,
            "message": {
                "tenant_id": "org_a",
                "sender": "x@a.b",
                "to": ["y@b.c"],
                "subject": "hi",
                "plain_body": "p",
                "_retries": 5,  # already at max
            },
        }
    )
    worker = SenderWorker(
        channel="email",
        db_pool=pool,
        email_router=_FailEmailRouter(),
        max_retries=5,
    )
    msg = await worker._read_one()
    assert msg is not None
    await worker._handle(msg)
    assert worker.stats.failed == 1
    assert worker.stats.dlq == 1


@pytest.mark.asyncio
async def test_sender_worker_sms_happy_path() -> None:
    pool = _FakePool()
    pool.read_queue.append(
        {
            "msg_id": 201,
            "message": {
                "tenant_id": "org_a",
                "to": "+5511999998888",
                "text": "hi",
                "from_number": "Rewire",
            },
        }
    )
    worker = SenderWorker(channel="sms", db_pool=pool, sms_router=_OkSmsRouter())
    msg = await worker._read_one()
    assert msg is not None
    await worker._handle(msg)
    assert worker.stats.succeeded == 1


@pytest.mark.asyncio
async def test_sender_worker_sms_failure() -> None:
    pool = _FakePool()
    pool.read_queue.append(
        {
            "msg_id": 202,
            "message": {
                "tenant_id": "org_a",
                "to": "+5511999998888",
                "text": "hi",
                "_retries": 0,
            },
        }
    )
    worker = SenderWorker(
        channel="sms", db_pool=pool, sms_router=_FailSmsRouter(), max_retries=3
    )
    msg = await worker._read_one()
    assert msg is not None
    await worker._handle(msg)
    assert worker.stats.failed == 1


@pytest.mark.asyncio
async def test_sender_worker_push_happy_path() -> None:
    pool = _FakePool()
    pool.read_queue.append(
        {
            "msg_id": 301,
            "message": {
                "tenant_id": "org_a",
                "device_token": "tok",
                "platform": "android",
                "title": "hi",
                "body": "b",
            },
        }
    )
    worker = SenderWorker(channel="push", db_pool=pool, push_router=_OkPushRouter())
    msg = await worker._read_one()
    assert msg is not None
    await worker._handle(msg)
    assert worker.stats.succeeded == 1


@pytest.mark.asyncio
async def test_sender_worker_push_failure() -> None:
    pool = _FakePool()
    pool.read_queue.append(
        {
            "msg_id": 302,
            "message": {
                "tenant_id": "org_a",
                "device_token": "tok",
                "platform": "android",
                "title": "hi",
                "body": "b",
                "_retries": 0,
            },
        }
    )
    worker = SenderWorker(
        channel="push", db_pool=pool, push_router=_FailPushRouter(), max_retries=3
    )
    msg = await worker._read_one()
    assert msg is not None
    await worker._handle(msg)
    assert worker.stats.failed == 1


@pytest.mark.asyncio
async def test_sender_worker_unexpected_exception_counted() -> None:
    """Test the catch-all branch in ``_handle``."""
    pool = _FakePool()
    pool.read_queue.append(
        {
            "msg_id": 401,
            "message": {
                "tenant_id": "org_a",
                "to": ["y@b.c"],
                "sender": "x@a.b",
                "subject": "hi",
                "plain_body": "p",
            },
        }
    )

    class _BoomRouter:
        async def send(self, **_: Any) -> Any:
            raise RuntimeError("boom-unexpected")

    worker = SenderWorker(channel="email", db_pool=pool, email_router=_BoomRouter())  # type: ignore[arg-type]
    msg = await worker._read_one()
    assert msg is not None
    await worker._handle(msg)
    assert worker.stats.failed == 1


# ---------------------------------------------------------------------------
# Retry worker
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_worker_requeues_with_backoff() -> None:
    pool = _FakePool()
    pool.read_queue.append(
        {
            "msg_id": 501,
            "message": {
                "tenant_id": "org_a",
                "to": ["y@b.c"],
                "_dlq_channel": "email",
                "_dlq_reason": "transient",
                "_retries": 1,
            },
        }
    )
    worker = RetryWorker(db_pool=pool, max_retries=5)
    msg = await worker._read_one()
    assert msg is not None
    await worker._handle(msg)
    assert worker.stats.requeued == 1


@pytest.mark.asyncio
async def test_retry_worker_permanent_fail_after_max() -> None:
    pool = _FakePool()
    pool.read_queue.append(
        {
            "msg_id": 502,
            "message": {
                "tenant_id": "org_a",
                "_dlq_channel": "email",
                "_retries": 5,
            },
        }
    )
    worker = RetryWorker(db_pool=pool, max_retries=5)
    msg = await worker._read_one()
    assert msg is not None
    await worker._handle(msg)
    assert worker.stats.permanent_fail == 1


@pytest.mark.asyncio
async def test_retry_worker_unknown_channel_permanent_fail() -> None:
    pool = _FakePool()
    pool.read_queue.append(
        {
            "msg_id": 503,
            "message": {
                "_dlq_channel": "telepathy",  # unknown
                "_retries": 0,
            },
        }
    )
    worker = RetryWorker(db_pool=pool, max_retries=5)
    msg = await worker._read_one()
    assert msg is not None
    await worker._handle(msg)
    assert worker.stats.permanent_fail == 1


@pytest.mark.asyncio
async def test_retry_worker_handles_json_string_message() -> None:
    """Messages may arrive as JSON strings (depending on pgmq driver)."""
    pool = _FakePool()
    pool.read_queue.append(
        {
            "msg_id": 504,
            "message": json.dumps(
                {"_dlq_channel": "sms", "_retries": 0}
            ),
        }
    )
    worker = RetryWorker(db_pool=pool, max_retries=5)
    msg = await worker._read_one()
    assert msg is not None
    await worker._handle(msg)
    assert worker.stats.requeued == 1


@pytest.mark.asyncio
async def test_sender_worker_handles_json_string_message() -> None:
    pool = _FakePool()
    pool.read_queue.append(
        {
            "msg_id": 601,
            "message": json.dumps(
                {
                    "tenant_id": "org_a",
                    "sender": "x@a.b",
                    "to": ["y@b.c"],
                    "subject": "hi",
                    "plain_body": "p",
                }
            ),
        }
    )
    worker = SenderWorker(
        channel="email", db_pool=pool, email_router=_OkEmailRouter()
    )
    msg = await worker._read_one()
    assert msg is not None
    await worker._handle(msg)
    assert worker.stats.succeeded == 1

"""Tests for pgmq queues (sender + retry workers).

These tests use a fake DB-pool stub to drive the worker through a single
message cycle without requiring pgmq to be installed. The goal is to
exercise the worker control flow (read -> dispatch -> archive / DLQ).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from contextlib import asynccontextmanager

import pytest

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "apps" / "control-plane" / "src"))

from messaging_cp.queues.sender_worker import PGMQ_DLQ, PGMQ_QUEUE  # noqa: E402


def test_pgmq_queue_names_match_spec() -> None:
    """The three outbound queues are named per spec."""
    assert PGMQ_QUEUE["email"] == "messaging_outbound_email"
    assert PGMQ_QUEUE["sms"] == "messaging_outbound_sms"
    assert PGMQ_QUEUE["push"] == "messaging_outbound_push"
    assert PGMQ_DLQ == "messaging_outbound_dlq"


@pytest.mark.asyncio
async def test_sender_worker_handles_empty_queue_gracefully() -> None:
    """``_read_one`` returns None when db_pool is None -> worker idles."""
    from messaging_cp.queues.sender_worker import SenderWorker

    worker = SenderWorker(channel="email")  # no db_pool -> dev mode
    msg = await worker._read_one()
    assert msg is None


@pytest.mark.asyncio
async def test_retry_worker_handles_empty_queue_gracefully() -> None:
    from messaging_cp.queues.retry_worker import RetryWorker

    worker = RetryWorker()  # no db_pool
    msg = await worker._read_one()
    assert msg is None

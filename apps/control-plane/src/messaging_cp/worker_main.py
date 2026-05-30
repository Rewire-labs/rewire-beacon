"""pgmq worker entrypoint — messaging_cp.worker_main.

RW-MESSAGING-14: SenderWorker + RetryWorker are implemented in
messaging_cp.queues but had no in-cluster Deployment.  This module is
the async entrypoint that a worker Deployment runs:

    CMD: python -m messaging_cp.worker_main

Environment variables (same ExternalSecret as control-plane):
  MESSAGING_DATABASE_URL   — asyncpg-compatible postgres URL
  MESSAGING_WORKER_CHANNEL — email | sms | push | retry  (default: email)
  MESSAGING_POLL_INTERVAL  — float seconds (default: 1.0)
  MESSAGING_VT_SECONDS     — visibility timeout seconds (default: 30)
  MESSAGING_MAX_RETRIES    — max retries before DLQ (default: 5)

NOTE: The Helm worker Deployment template lives in
  architecture/products/messaging/helm/templates/worker.yaml
(cluster_root — blocked for this agent; to be added by cluster eng).
Until that Deployment exists, async_mode=true in the API will enqueue
to pgmq but no consumer will drain the queue.
"""

from __future__ import annotations

import asyncio
import logging
import os

logger = logging.getLogger(__name__)


async def _run_sender(channel: str, db_url: str) -> None:
    import asyncpg

    from messaging_cp.queues.sender_worker import SenderWorker

    poll_interval = float(os.environ.get("MESSAGING_POLL_INTERVAL", "1.0"))
    vt_seconds = int(os.environ.get("MESSAGING_VT_SECONDS", "30"))
    max_retries = int(os.environ.get("MESSAGING_MAX_RETRIES", "5"))

    logger.info("messaging.worker.connecting", channel=channel)
    pool = await asyncpg.create_pool(db_url, min_size=1, max_size=4)
    try:
        worker = SenderWorker(
            channel=channel,  # type: ignore[arg-type]
            db_pool=pool,
            poll_interval_seconds=poll_interval,
            visibility_timeout_seconds=vt_seconds,
            max_retries=max_retries,
        )
        await worker.run_forever()
    finally:
        await pool.close()


async def _run_retry(db_url: str) -> None:
    import asyncpg

    from messaging_cp.queues.retry_worker import RetryWorker

    poll_interval = float(os.environ.get("MESSAGING_POLL_INTERVAL", "5.0"))
    max_retries = int(os.environ.get("MESSAGING_MAX_RETRIES", "5"))

    logger.info("messaging.retry_worker.connecting")
    pool = await asyncpg.create_pool(db_url, min_size=1, max_size=2)
    try:
        worker = RetryWorker(db_pool=pool, poll_interval_seconds=poll_interval, max_retries=max_retries)
        await worker.run_forever()
    finally:
        await pool.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    db_url = os.environ.get("MESSAGING_DATABASE_URL", "")
    if not db_url:
        raise SystemExit("MESSAGING_DATABASE_URL is required for worker mode")

    channel = os.environ.get("MESSAGING_WORKER_CHANNEL", "email").lower()
    logger.info("messaging.worker.starting", channel=channel)

    if channel == "retry":
        asyncio.run(_run_retry(db_url))
    elif channel in ("email", "sms", "push"):
        asyncio.run(_run_sender(channel, db_url))
    else:
        raise SystemExit(f"Unknown MESSAGING_WORKER_CHANNEL={channel!r}; use email|sms|push|retry")


if __name__ == "__main__":
    main()

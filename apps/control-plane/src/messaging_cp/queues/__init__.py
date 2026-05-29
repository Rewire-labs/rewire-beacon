"""pgmq queue workers for rewire-messaging (V0).

Queues (pgmq):
  - messaging_outbound_email
  - messaging_outbound_sms
  - messaging_outbound_push

Decision (Slot 4 Run 4): pgmq + pg_cron replaces the legacy Kafka topology
declared in BEACON spec. The legacy ``beacon.workers.*`` Kafka consumers
remain available for production migration paths but new control-plane code
uses pgmq.

Reason: ADR-aligned Stream-less stack (REALTIME covers; queues via DATABASES
pgmq). One Postgres extension == one less moving part for V0.
"""

from __future__ import annotations

from messaging_cp.queues.sender_worker import SenderWorker
from messaging_cp.queues.retry_worker import RetryWorker

__all__ = ["SenderWorker", "RetryWorker"]

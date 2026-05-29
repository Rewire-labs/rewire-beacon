"""Create pgmq queues for outbound messaging (MSG-V0 Slot 4 Run 4).

Replaces the legacy Kafka topology declared in BEACON spec with pgmq +
pg_cron, aligned with the global decision (REALTIME covers; queues via
DATABASES pgmq + pg_cron). One Postgres extension == one less moving part.

Queues created:
  - messaging_outbound_email  (sender_worker target)
  - messaging_outbound_sms
  - messaging_outbound_push
  - messaging_outbound_dlq    (retry_worker drains here)

The migration is idempotent: ``pgmq.create()`` checks existence internally
and no-ops on second run.

Revision ID: 0005_pgmq_queues
Revises: 0004_beacon_worker_role
Create Date: 2026-05-25
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0005_pgmq_queues"
down_revision: str | Sequence[str] | None = "0004_beacon_worker_role"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


QUEUES = [
    "messaging_outbound_email",
    "messaging_outbound_sms",
    "messaging_outbound_push",
    "messaging_outbound_dlq",
]


def upgrade() -> None:
    # Enable pgmq extension (idempotent). DATABASES product owns the
    # cluster-wide install — this CREATE EXTENSION IF NOT EXISTS is
    # defensive for tenant-level DB bootstraps.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgmq CASCADE")

    for q in QUEUES:
        # ``pgmq.create()`` is idempotent on the queue table itself.
        op.execute(f"SELECT pgmq.create('{q}')")


def downgrade() -> None:
    for q in reversed(QUEUES):
        op.execute(f"SELECT pgmq.drop_queue('{q}')")
    # Extension drop is intentionally omitted to avoid affecting other
    # products on the shared cluster.

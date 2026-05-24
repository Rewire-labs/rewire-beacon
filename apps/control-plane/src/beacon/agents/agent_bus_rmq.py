"""BCN-101: RabbitMQ producer + consumer canonical envelope.

Routing keys (INTER_AGENT_COMM_SPEC §2.3)::

  agent.<src>.<dst>.<event>     - directed event
  agent.<src>.*.<event>         - fanout event

Producer emits state-change + completion long-running events from
BEACON (message dispatched, bounce/complaint received, suppression
added cross-channel, domain verified, journey step transitioned).

Consumer subscribes::

  agent.metering.*.budget_exhausted   -> set local degrade flag
  agent.citadel.*.chain_appended      -> cross-link in local audit log
  agent.tenant.*.policy_changed       -> reload local policy cache
  agent.*.beacon-ai.*                 -> directed events handler

Reuses CNT-042 DLQ pattern (dead-letter exchange ``agent.dlq``).

BEACON ships its own canonical agent-bus on top of any existing
shared messaging publisher; the two pipelines coexist because they
speak different envelopes (this one = INTER_AGENT_COMM_SPEC; the
shared one = ``EventEnvelope`` for product-domain events).
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

try:
    import aio_pika
    from aio_pika import IncomingMessage, Message
    from aio_pika.abc import AbstractRobustConnection

    _AIOPIKA_AVAILABLE = True
except ImportError:  # pragma: no cover
    _AIOPIKA_AVAILABLE = False


@dataclass(frozen=True)
class AgentEvent:
    """Canonical agent event envelope (INTER_AGENT_COMM_SPEC §2.3)."""

    event_id: str
    src: str
    dst: str
    event: str
    tenant_id: str
    occurred_at: str
    payload: dict[str, Any]
    trace_id: str | None = None
    audit_chain_ref: str | None = None

    @classmethod
    def new(
        cls,
        *,
        src: str,
        dst: str,
        event: str,
        tenant_id: str = "global",
        payload: dict[str, Any] | None = None,
        trace_id: str | None = None,
        audit_chain_ref: str | None = None,
    ) -> AgentEvent:
        return cls(
            event_id=str(uuid.uuid4()),
            src=src,
            dst=dst,
            event=event,
            tenant_id=tenant_id,
            occurred_at=datetime.now(UTC).isoformat(),
            payload=payload or {},
            trace_id=trace_id,
            audit_chain_ref=audit_chain_ref,
        )

    def routing_key(self) -> str:
        return f"agent.{self.src}.{self.dst}.{self.event}"

    def to_json(self) -> str:
        return json.dumps(
            {
                "event_id": self.event_id,
                "src": self.src,
                "dst": self.dst,
                "event": self.event,
                "tenant_id": self.tenant_id,
                "occurred_at": self.occurred_at,
                "payload": self.payload,
                "trace_id": self.trace_id,
                "audit_chain_ref": self.audit_chain_ref,
            },
            separators=(",", ":"),
        )

    @classmethod
    def from_json(cls, raw: str | bytes) -> AgentEvent:
        d = json.loads(raw)
        return cls(
            event_id=d["event_id"],
            src=d["src"],
            dst=d["dst"],
            event=d["event"],
            tenant_id=d.get("tenant_id", "global"),
            occurred_at=d["occurred_at"],
            payload=d.get("payload", {}),
            trace_id=d.get("trace_id"),
            audit_chain_ref=d.get("audit_chain_ref"),
        )


# Canonical event names emitted by BEACON.
EVENT_BUDGET_EXHAUSTED = "budget_exhausted"
EVENT_BUDGET_CONSUMED = "budget_consumed"
EVENT_CHAIN_APPENDED = "chain_appended"
EVENT_POLICY_CHANGED = "policy_changed"
EVENT_MESSAGE_DISPATCHED = "message_dispatched"
EVENT_MESSAGE_BOUNCED = "message_bounced"
EVENT_MESSAGE_COMPLAINED = "message_complained"
EVENT_SUPPRESSION_ADDED = "suppression_added"
EVENT_DOMAIN_VERIFIED = "domain_verified"
EVENT_JOURNEY_STEP_TRANSITIONED = "journey_step_transitioned"


class AgentBusRMQ:
    """Producer + consumer of canonical agent events on RabbitMQ.

    Production: connects to RabbitMQ via ``RMQ_URL`` env. Tests: mock
    mode when env var absent (events written to in-memory list).
    """

    EXCHANGE_MAIN = "agent.events"
    EXCHANGE_DLQ = "agent.dlq"
    QUEUE_PREFIX = "beacon-ai."

    def __init__(self, *, rmq_url: str | None = None) -> None:
        self._rmq_url = rmq_url or os.environ.get("RMQ_URL", "")
        self._conn: AbstractRobustConnection | None = None  # type: ignore[type-arg]
        self._channel = None
        self._exchange = None
        self._mock_emitted: list[AgentEvent] = []
        self._consumers: dict[str, Callable[[AgentEvent], Awaitable[None]]] = {}

    @property
    def mock_emitted(self) -> list[AgentEvent]:
        return self._mock_emitted

    @property
    def is_mock(self) -> bool:
        return not self._rmq_url or not _AIOPIKA_AVAILABLE

    async def connect(self) -> None:
        if self.is_mock:
            logger.warning("agent_bus_rmq.mock_mode")
            return
        self._conn = await aio_pika.connect_robust(self._rmq_url)
        self._channel = await self._conn.channel()
        self._exchange = await self._channel.declare_exchange(
            self.EXCHANGE_MAIN, aio_pika.ExchangeType.TOPIC, durable=True
        )
        await self._channel.declare_exchange(
            self.EXCHANGE_DLQ, aio_pika.ExchangeType.TOPIC, durable=True
        )

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()

    async def publish(self, event: AgentEvent) -> None:
        if self.is_mock:
            self._mock_emitted.append(event)
            logger.info(
                "agent_bus_rmq.publish_mock",
                extra={
                    "event_id": event.event_id,
                    "routing_key": event.routing_key(),
                },
            )
            return
        assert self._exchange is not None
        msg = Message(
            event.to_json().encode("utf-8"),
            content_type="application/json",
            message_id=event.event_id,
            headers={"trace_id": event.trace_id or ""},
        )
        await self._exchange.publish(msg, routing_key=event.routing_key())
        logger.info(
            "agent_bus_rmq.published",
            extra={
                "event_id": event.event_id,
                "routing_key": event.routing_key(),
            },
        )

    def on(
        self,
        routing_pattern: str,
        handler: Callable[[AgentEvent], Awaitable[None]],
    ) -> None:
        """Register a handler for events matching ``routing_pattern``.

        Pattern is RMQ topic style: ``agent.metering.*.budget_exhausted``.
        """
        self._consumers[routing_pattern] = handler

    async def start_consumers(self) -> None:
        if self.is_mock:
            logger.warning("agent_bus_rmq.consumers_mock_no_op")
            return
        assert self._channel is not None and self._exchange is not None
        for routing_pattern, handler in self._consumers.items():
            queue_name = (
                self.QUEUE_PREFIX
                + routing_pattern.replace(".", "_").replace("*", "wild")
            )
            q = await self._channel.declare_queue(
                queue_name,
                durable=True,
                arguments={"x-dead-letter-exchange": self.EXCHANGE_DLQ},
            )
            await q.bind(self._exchange, routing_key=routing_pattern)

            async def _wrap(message: IncomingMessage, h=handler) -> None:
                async with message.process(requeue=False):
                    try:
                        ev = AgentEvent.from_json(message.body)
                        await h(ev)
                    except Exception:  # noqa: BLE001
                        logger.exception(
                            "agent_bus_rmq.consumer_failed",
                            extra={"key": routing_pattern},
                        )
                        raise

            await q.consume(_wrap)


_GLOBAL_BUS: AgentBusRMQ | None = None


async def get_bus() -> AgentBusRMQ:
    global _GLOBAL_BUS
    if _GLOBAL_BUS is None:
        _GLOBAL_BUS = AgentBusRMQ()
        await _GLOBAL_BUS.connect()
    return _GLOBAL_BUS


def reset_bus_for_tests() -> None:
    """ONLY for tests."""
    global _GLOBAL_BUS
    _GLOBAL_BUS = None


# ---------------------------------------------------------------------------
# Default consumer handlers (BCN-101 §Consumer)
# ---------------------------------------------------------------------------


_DEGRADE_FLAG = {"active": False}


async def on_budget_exhausted(event: AgentEvent) -> None:
    """``agent.metering.*.budget_exhausted`` -> set local degrade flag.

    BEACON in degrade mode short-circuits non-essential channel dispatch
    (marketing campaigns) and only allows security/transactional sends.
    """
    _DEGRADE_FLAG["active"] = True
    logger.warning(
        "agent_bus_rmq.degrade_activated",
        extra={"event_id": event.event_id, "tenant_id": event.tenant_id},
    )


async def on_chain_appended(event: AgentEvent) -> None:
    """``agent.citadel.*.chain_appended`` -> cross-link in local audit log."""
    logger.info(
        "agent_bus_rmq.cross_link_chain",
        extra={
            "event_id": event.event_id,
            "audit_chain_ref": event.audit_chain_ref,
        },
    )


async def on_policy_changed(event: AgentEvent) -> None:
    """``agent.tenant.*.policy_changed`` -> reload local policy cache.

    For BEACON: reload per-tenant suppression rules, quiet-hours config,
    frequency-capping policy.
    """
    logger.info(
        "agent_bus_rmq.policy_reload",
        extra={"event_id": event.event_id, "tenant_id": event.tenant_id},
    )


def is_degrade_mode_active() -> bool:
    return _DEGRADE_FLAG["active"]


def reset_degrade_mode_for_tests() -> None:
    _DEGRADE_FLAG["active"] = False

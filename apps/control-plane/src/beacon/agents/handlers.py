"""BCN-AICX-01: capability handlers — capability_id -> coroutine dispatch.

Each handler:
- Takes ``(input: dict, ctx: HandlerContext)`` and returns ``HandlerResult``
- Validates input against the capability's ``input_schema`` (caller-side
  via the agent_invoke_router using jsonschema lib if available).
- Wraps the underlying domain operation (send_email, send_sms,
  suppression, list_messages).

Adding a new capability requires:
  1. add entry to ``capabilities.yaml``
  2. add handler here
  3. add entry to ``HANDLERS`` dict at bottom
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HandlerContext:
    """Shared per-call state for handlers."""

    tenant_id: str
    actor_sub: str
    capability_id: str
    trace_id: str
    chain_ref_in: str | None
    deadline_ms: int
    max_cost_usd: float


@dataclass(frozen=True)
class HandlerResult:
    """Returned by handlers. ``cost_usd`` may be 0.0 for deterministic ops."""

    output: dict[str, Any]
    cost_usd: float = 0.0
    audit_chain_hash: str | None = None
    error: dict[str, Any] | None = None


Handler = Callable[[dict[str, Any], HandlerContext], Awaitable[HandlerResult]]


def _synth_chain_hash(*parts: str) -> str:
    """Deterministic synthetic BLAKE3-style chain hash for V0.

    Production wires this to the CITADEL chain anchor — for V0 we use a
    deterministic SHA-256 over the input parts (chain_ref_in + payload)
    so idempotent replays produce the same hash and tests can assert.
    """
    h = hashlib.sha256()
    for p in parts:
        h.update((p or "").encode("utf-8"))
        h.update(b"\x1f")
    return f"blake3:{h.hexdigest()[:48]}"


# ---------------------------------------------------------------------------
# Handler implementations
# ---------------------------------------------------------------------------


async def send_email(input_: dict[str, Any], ctx: HandlerContext) -> HandlerResult:
    """Enqueue a transactional email (via existing /v1/messages/email path).

    V0 returns a deterministic synthetic message_id + chain_hash; production
    delegates to ``beacon.services.messaging.enqueue_email`` so the
    canonical contract is exercised end-to-end even when the underlying
    dispatcher is not wired (smoke tests pass).
    """
    tenant_id = str(input_["tenant_id"])
    sender = str(input_["sender"])
    to_list = list(input_["to"])
    subject = str(input_["subject"])
    consent = str(input_["consent_basis"])
    template_slug = input_.get("template_slug") or ""

    # Deterministic synthetic id derived from (tenant_id, sender, to, subject).
    seed = f"{tenant_id}|{sender}|{','.join(to_list)}|{subject}|{template_slug}"
    msg_id = "msg_" + uuid.uuid5(uuid.NAMESPACE_URL, seed).hex[:24]
    chain_hash = _synth_chain_hash(
        ctx.chain_ref_in or "",
        tenant_id,
        sender,
        ",".join(to_list),
        subject,
        consent,
    )
    return HandlerResult(
        output={
            "message_id": msg_id,
            "status": "queued",
            "chain_hash": chain_hash,
            "provider_route": "postal",
        },
        audit_chain_hash=chain_hash,
    )


async def send_sms(input_: dict[str, Any], ctx: HandlerContext) -> HandlerResult:
    """Enqueue an SMS via BR BSP routing."""
    tenant_id = str(input_["tenant_id"])
    to = str(input_["to"])
    text = str(input_["text"])
    consent = str(input_["consent_basis"])
    seed = f"{tenant_id}|{to}|{text}"
    msg_id = "sms_" + uuid.uuid5(uuid.NAMESPACE_URL, seed).hex[:24]
    chain_hash = _synth_chain_hash(
        ctx.chain_ref_in or "", tenant_id, to, text[:128], consent
    )
    return HandlerResult(
        output={
            "message_id": msg_id,
            "status": "queued",
            "chain_hash": chain_hash,
            "provider_route": "zenvia",
        },
        audit_chain_hash=chain_hash,
    )


async def send_whatsapp(
    input_: dict[str, Any], ctx: HandlerContext
) -> HandlerResult:
    """Enqueue a WhatsApp message via CONNECT BSP."""
    tenant_id = str(input_["tenant_id"])
    to = str(input_["to"])
    template_name = str(input_["template_name"])
    consent = str(input_["consent_basis"])
    seed = f"{tenant_id}|{to}|{template_name}"
    msg_id = "wa_" + uuid.uuid5(uuid.NAMESPACE_URL, seed).hex[:24]
    chain_hash = _synth_chain_hash(
        ctx.chain_ref_in or "", tenant_id, to, template_name, consent
    )
    return HandlerResult(
        output={
            "message_id": msg_id,
            "status": "queued",
            "chain_hash": chain_hash,
            "provider_route": "connect_whatsapp",
        },
        audit_chain_hash=chain_hash,
    )


async def add_suppression(
    input_: dict[str, Any], ctx: HandlerContext
) -> HandlerResult:
    """Add an identifier to the cross-channel suppression list."""
    tenant_id = str(input_["tenant_id"])
    itype = str(input_["identifier_type"])
    ivalue = str(input_["identifier_value"])
    reason = str(input_.get("reason", "manual"))
    sup_id = str(
        uuid.uuid5(uuid.NAMESPACE_URL, f"beacon:supp:{tenant_id}:{itype}:{ivalue}")
    )
    chain_hash = _synth_chain_hash(
        ctx.chain_ref_in or "", tenant_id, itype, ivalue, reason
    )
    return HandlerResult(
        output={
            "id": sup_id,
            "identifier_type": itype,
            "identifier_value": ivalue,
            "reason": reason,
            "created_at": datetime.now(UTC).isoformat(),
        },
        audit_chain_hash=chain_hash,
    )


async def check_suppression(
    input_: dict[str, Any], ctx: HandlerContext
) -> HandlerResult:
    """Check if an identifier is suppressed (V0 returns false by default).

    Production wires this to ``beacon.services.suppression.check`` for
    a <2ms hot path (Redis-backed cross-channel cache).
    """
    tenant_id = str(input_["tenant_id"])
    itype = str(input_["identifier_type"])
    ivalue = str(input_["identifier_value"])
    # V0 deterministic: synthetic non-suppressed unless ivalue contains "blocked".
    suppressed = "blocked" in ivalue.lower()
    out: dict[str, Any] = {"tenant_id": tenant_id, "suppressed": suppressed}
    if suppressed:
        out["reason"] = "bounce_hard"
        out["created_at"] = datetime.now(UTC).isoformat()
    return HandlerResult(output=out)


async def list_messages(
    input_: dict[str, Any], ctx: HandlerContext
) -> HandlerResult:
    """Returns recent messages for a tenant (V0 empty list, schema-stable)."""
    tenant_id = str(input_["tenant_id"])
    limit = int(input_.get("limit", 100))
    return HandlerResult(
        output={
            "tenant_id": tenant_id,
            "count": 0,
            "messages": [],
            "_meta": {"limit": limit, "v0_stub": True},
        },
    )


# ---------------------------------------------------------------------------
# Registry — capability_id -> handler
# ---------------------------------------------------------------------------

# RW-MESSAGING-10: canonical capability_id prefix is rewire.messaging.*
# Legacy rewire.beacon.* aliases kept for 90d migration window so existing
# agent callers (rewire-nova, rewire-admin) don't break on upgrade.
HANDLERS: dict[str, Handler] = {
    # Canonical (new)
    "rewire.messaging.send_email": send_email,
    "rewire.messaging.send_sms": send_sms,
    "rewire.messaging.send_whatsapp": send_whatsapp,
    "rewire.messaging.add_suppression": add_suppression,
    "rewire.messaging.check_suppression": check_suppression,
    "rewire.messaging.list_messages": list_messages,
    # Legacy aliases (90d deprecation window — remove after 2026-08-28)
    "rewire.beacon.send_email": send_email,
    "rewire.beacon.send_sms": send_sms,
    "rewire.beacon.send_whatsapp": send_whatsapp,
    "rewire.beacon.add_suppression": add_suppression,
    "rewire.beacon.check_suppression": check_suppression,
    "rewire.beacon.list_messages": list_messages,
}


def get_handler(capability_id: str) -> Handler | None:
    return HANDLERS.get(capability_id)

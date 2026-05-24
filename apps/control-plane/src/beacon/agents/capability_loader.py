"""BCN-CAP-01: capability registry loader + ETag computation.

Reads ``capabilities.yaml`` at boot (path injected via
``BEACON_CAPABILITIES_PATH`` env or repo root). Validates against the
canonical schema (minimal local copy — full validation in CI via the
``rewire_shared.capability_schema`` lib). Computes a deterministic ETag
from ``sha256(canonical_json)`` so clients can cache via 304.

Designed to be 1:1 compatible with the PULSE-CLOUD + CITADEL-CLOUD
reference impls so the chat-orchestrator can probe all services with
the same client.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


CAPABILITY_ID_REGEX = r"^rewire\.[a-z][a-z0-9-]*\.[a-z][a-z0-9_]*$"

REQUIRED_TOP_LEVEL = ("service", "version", "capabilities")
REQUIRED_PER_CAP = (
    "id",
    "name",
    "description",
    "version",
    "category",
    "invoke",
    "budget",
    "permissions",
    "audit",
    "deprecation",
)
REQUIRED_INVOKE = ("transport", "endpoint", "schema")
REQUIRED_BUDGET = ("per_call_max_seconds",)
REQUIRED_PERMS = ("requires_oauth", "scopes", "requires_hitl", "sensitivity")
REQUIRED_AUDIT = ("emit_event",)


class CapabilityLoadError(ValueError):
    """Raised when capabilities.yaml is malformed."""


@dataclass(frozen=True)
class Capability:
    """Parsed capability entry with input/output JSON Schemas."""

    id: str
    name: str
    description: str
    version: str
    category: str
    endpoint: str
    transport: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    budget_max_seconds: int = 30
    budget_tokens: int = 0
    requires_oauth: bool = True
    scopes: tuple[str, ...] = ()
    requires_hitl: bool = False
    sensitivity: str = "low"
    audit_event: str = ""
    deprecated_at: str | None = None
    sunset_at: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CapabilityRegistry:
    """Immutable snapshot served by GET /api/v1/capabilities."""

    service: str
    version: str
    capabilities: tuple[Capability, ...]
    canonical_json: str
    etag: str

    def by_id(self, capability_id: str) -> Capability | None:
        for c in self.capabilities:
            if c.id == capability_id:
                return c
        return None


def _validate(payload: dict[str, Any]) -> None:
    """Defensive validation — boot fails fast on malformed YAML."""
    missing = [k for k in REQUIRED_TOP_LEVEL if k not in payload]
    if missing:
        raise CapabilityLoadError(f"missing_top_level_keys:{missing}")
    if not isinstance(payload["capabilities"], list):
        raise CapabilityLoadError("capabilities_must_be_list")
    if not payload["capabilities"]:
        raise CapabilityLoadError("capabilities_must_not_be_empty")
    seen_ids: set[str] = set()
    for i, cap in enumerate(payload["capabilities"]):
        for key in REQUIRED_PER_CAP:
            if key not in cap:
                raise CapabilityLoadError(f"cap[{i}].missing:{key}")
        for key in REQUIRED_INVOKE:
            if key not in cap["invoke"]:
                raise CapabilityLoadError(f"cap[{i}].invoke.missing:{key}")
        if (
            "input" not in cap["invoke"]["schema"]
            or "output" not in cap["invoke"]["schema"]
        ):
            raise CapabilityLoadError(
                f"cap[{i}].invoke.schema.missing_input_or_output"
            )
        for key in REQUIRED_BUDGET:
            if key not in cap["budget"]:
                raise CapabilityLoadError(f"cap[{i}].budget.missing:{key}")
        for key in REQUIRED_PERMS:
            if key not in cap["permissions"]:
                raise CapabilityLoadError(f"cap[{i}].permissions.missing:{key}")
        for key in REQUIRED_AUDIT:
            if key not in cap["audit"]:
                raise CapabilityLoadError(f"cap[{i}].audit.missing:{key}")
        if cap["id"] in seen_ids:
            raise CapabilityLoadError(f"cap[{i}].duplicate_id:{cap['id']}")
        seen_ids.add(cap["id"])


def _parse_capability(cap: dict[str, Any]) -> Capability:
    invoke = cap["invoke"]
    budget = cap["budget"]
    perms = cap["permissions"]
    audit = cap["audit"]
    deprec = cap.get("deprecation", {}) or {}
    return Capability(
        id=str(cap["id"]),
        name=str(cap["name"]),
        description=str(cap["description"]),
        version=str(cap["version"]),
        category=str(cap["category"]),
        endpoint=str(invoke["endpoint"]),
        transport=str(invoke["transport"]),
        input_schema=invoke["schema"]["input"],
        output_schema=invoke["schema"]["output"],
        budget_max_seconds=int(budget.get("per_call_max_seconds", 30)),
        budget_tokens=int(budget.get("per_call_tokens", 0) or 0),
        requires_oauth=bool(perms.get("requires_oauth", True)),
        scopes=tuple(perms.get("scopes", []) or []),
        requires_hitl=bool(perms.get("requires_hitl", False)),
        sensitivity=str(perms.get("sensitivity", "low")),
        audit_event=str(audit.get("emit_event", "")),
        deprecated_at=deprec.get("deprecated_at"),
        sunset_at=deprec.get("sunset_at"),
        raw=cap,
    )


def load_capability_registry(yaml_path: Path | str) -> CapabilityRegistry:
    """Parse + validate + freeze a registry snapshot.

    Raises ``CapabilityLoadError`` on any structural issue.
    """
    p = Path(yaml_path)
    if not p.exists():
        raise CapabilityLoadError(f"file_not_found:{p}")
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise CapabilityLoadError("yaml_root_must_be_mapping")
    _validate(raw)
    capabilities = tuple(_parse_capability(c) for c in raw["capabilities"])
    # Canonical JSON for ETag — sorted keys, separators tight.
    canonical = json.dumps(
        raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    etag = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    reg = CapabilityRegistry(
        service=str(raw["service"]),
        version=str(raw["version"]),
        capabilities=capabilities,
        canonical_json=canonical,
        etag=f'W/"{etag[:32]}"',
    )
    logger.info(
        "capability_registry.loaded",
        extra={"count": len(capabilities), "etag": reg.etag, "service": reg.service},
    )
    return reg


@lru_cache(maxsize=1)
def get_registry() -> CapabilityRegistry:
    """Cached global registry. Reloaded only on process restart."""
    import os

    path_env = os.environ.get("BEACON_CAPABILITIES_PATH")
    if path_env:
        return load_capability_registry(path_env)

    # Defaults: try (a) cwd, (b) repo-root level, (c) /etc/beacon/.
    candidates = [
        Path.cwd() / "capabilities.yaml",
        Path(__file__).resolve().parents[5] / "capabilities.yaml",
        Path("/etc/beacon/capabilities.yaml"),
    ]
    for c in candidates:
        if c.exists():
            return load_capability_registry(c)
    raise CapabilityLoadError(
        f"no_capabilities_yaml_found_in:{[str(c) for c in candidates]}"
    )


def reset_registry_cache_for_tests() -> None:
    """ONLY for tests — clears the lru_cache so a fresh YAML can be loaded."""
    get_registry.cache_clear()

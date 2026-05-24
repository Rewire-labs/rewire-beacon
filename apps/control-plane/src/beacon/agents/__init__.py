"""BEACON agents subpackage — capability registry + inter-agent comm.

Modules:
- capability_loader: parse capabilities.yaml at boot, ETag-aware exposure
- handlers: per-capability operation handlers (deterministic V0)
- agent_bus_client: cross-agent REST client (BCN-100/102/103)
- agent_bus_rmq: cross-agent RMQ producer/consumer (BCN-101)

Routers (mounted in main.py):
- capabilities_router: GET /api/v1/capabilities  (BCN-CAP-01)
- agent_invoke_router: POST /agent/v1/invoke    (BCN-AICX-01)
"""

from __future__ import annotations

__all__ = [
    "capability_loader",
    "handlers",
    "agent_bus_client",
    "agent_bus_rmq",
]

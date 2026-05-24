"""BCN-CAP-01: ``GET /api/v1/capabilities`` canonical endpoint.

- ETag support (304 on ``If-None-Match`` match)
- Public: no auth required (registry is intentionally public; sensitive
  details are NOT in capability descriptions — only contracts).
- Mirrors PULSE-CLOUD + CITADEL-CLOUD impl so chat-orchestrator can
  probe all services with the same client.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Request, Response, status

from .capability_loader import CapabilityLoadError, get_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["capabilities"])


@router.get(
    "/capabilities",
    summary="BEACON capability registry (canonical REST)",
    description=(
        "Returns the canonical capability registry of this service. "
        "ETag header supports 304 Not Modified via If-None-Match."
    ),
    responses={
        200: {"description": "Registry payload"},
        304: {"description": "Not modified (ETag matched)"},
        500: {"description": "Registry malformed (boot failure)"},
    },
)
async def get_capabilities(request: Request, response: Response) -> Response:
    try:
        reg = get_registry()
    except CapabilityLoadError as e:
        logger.exception("capability_registry.load_failed", extra={"err": str(e)})
        return Response(
            content=json.dumps({"error": "registry_load_failed", "detail": str(e)}),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            media_type="application/json",
        )

    if_none = request.headers.get("If-None-Match")
    if if_none and if_none.strip() == reg.etag:
        return Response(
            status_code=status.HTTP_304_NOT_MODIFIED, headers={"ETag": reg.etag}
        )

    body = {
        "service": reg.service,
        "version": reg.version,
        "etag": reg.etag,
        "capabilities": [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "version": c.version,
                "category": c.category,
                "agent_endpoint": "/agent/v1/invoke",
                "invoke": {
                    "transport": c.transport,
                    "endpoint": c.endpoint,
                    "schema": {"input": c.input_schema, "output": c.output_schema},
                },
                "budget": {
                    "per_call_max_seconds": c.budget_max_seconds,
                    "per_call_tokens": c.budget_tokens,
                },
                "permissions": {
                    "requires_oauth": c.requires_oauth,
                    "scopes": list(c.scopes),
                    "requires_hitl": c.requires_hitl,
                    "sensitivity": c.sensitivity,
                },
                "audit": {"emit_event": c.audit_event},
                "deprecation": {
                    "deprecated_at": c.deprecated_at,
                    "sunset_at": c.sunset_at,
                },
            }
            for c in reg.capabilities
        ],
    }
    return Response(
        content=json.dumps(body, separators=(",", ":")),
        media_type="application/json",
        headers={"ETag": reg.etag, "Cache-Control": "public, max-age=300"},
    )

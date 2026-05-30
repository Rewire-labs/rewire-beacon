"""POST /v1/webhooks/{provider} — inbound provider webhooks.

Providers handled:
  - postal   — delivery/bounce/complaint events
  - resend   — delivery webhook
  - zenvia   — SMS status callback
  - apns     — feedback service (bad tokens)
  - fcm      — topic subscription / unregistration

Each provider has its own signature scheme; verification lives in the
legacy ``beacon.api.webhooks_inbound`` module. This canonical surface
delegates to that handler to avoid duplicating signature code.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/webhooks")

SupportedProvider = Literal["postal", "resend", "zenvia", "apns", "fcm"]


@router.post(
    "/{provider}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Inbound webhook from an upstream provider",
)
async def inbound_webhook(provider: str, request: Request) -> None:
    """Generic inbound webhook proxy.

    Delegates to ``beacon.api.webhooks_inbound`` providers via dynamic
    dispatch. Returns 204 on success, 400 on signature/payload error.
    """
    if provider not in {"postal", "resend", "zenvia", "apns", "fcm"}:
        raise HTTPException(
            status_code=404,
            detail={"error": "unknown_provider", "supported": list(SupportedProvider.__args__)},  # type: ignore[attr-defined]
        )
    body = await request.body()
    sig = request.headers.get("X-Webhook-Signature", "")
    logger.info(
        "messaging.webhook.received",
        extra={"provider": provider, "size": len(body), "has_sig": bool(sig)},
    )
    # V0: parse minimal envelope; legacy handler in beacon.api.webhooks_inbound
    # performs the actual signature verification + event persistence.
    try:
        from beacon.api.webhooks_inbound import dispatch_provider_event  # type: ignore

        await dispatch_provider_event(provider=provider, body=body, signature=sig)
    except ImportError:
        # Legacy handler absent in some build profiles — accept and log.
        logger.debug(
            "messaging.webhook.legacy_handler_missing",
            extra={"provider": provider},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "messaging.webhook.handler_failed",
            extra={"provider": provider, "error": str(exc)},
        )
        raise HTTPException(
            status_code=400,
            detail={"error": "webhook_processing_failed", "message": str(exc)},
        ) from exc


__all__ = ["router"]

"""V0 stub — inbound webhook receivers (Postal / Zenvia / FCM / APNs ACKs)."""

from __future__ import annotations

from fastapi import APIRouter, Request, status

router = APIRouter()


@router.post(
    "/webhooks/{provider}",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive provider event webhook (V0 STUB)",
)
async def receive_webhook(provider: str, request: Request) -> dict[str, object]:
    """V0 stub — providers: postal | zenvia | totalvoice | fcm | apns | connect.

    V0.2: HMAC signature verify per provider + enqueue to RabbitMQ event topic
    for the Event Ingest worker to normalize and stream into ClickHouse.
    """
    body_bytes = await request.body()
    return {
        "status": "not_implemented",
        "todo": "V0.2 — verify HMAC + normalize + enqueue to event ingest",
        "provider": provider,
        "received_bytes": len(body_bytes),
    }

"""Idempotency middleware: Redis-backed dedupe for write endpoints.

Behaviour:
- Only applies to POST/PUT/PATCH/DELETE.
- Reads `Idempotency-Key` header (UUID/ULID).
- Computes SHA256 of (org_id|method|path|key|body) and stores body+response
  in Redis with 24h TTL.
- On repeat call with same key, returns cached response (status + body).

Falls back to no-op when Redis is unavailable.
"""
from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from beacon.settings import get_settings

logger = logging.getLogger(__name__)

IDEMPOTENT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
TTL_SECONDS = 24 * 3600


class IdempotencyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._settings = get_settings()
        self._redis = None

    async def _get_redis(self):  # noqa: ANN202
        if self._redis is not None:
            return self._redis
        try:
            from redis.asyncio import Redis  # type: ignore

            self._redis = Redis.from_url(self._settings.redis_url, decode_responses=True)
            await self._redis.ping()
        except Exception as exc:  # noqa: BLE001
            logger.debug("redis unavailable, idempotency disabled: %s", exc)
            self._redis = None
        return self._redis

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method not in IDEMPOTENT_METHODS:
            return await call_next(request)
        idem_key = request.headers.get("Idempotency-Key")
        if not idem_key:
            return await call_next(request)

        redis = await self._get_redis()
        if redis is None:
            return await call_next(request)

        org_id = getattr(request.state, "organization_id", "global")
        body = await request.body()
        digest = hashlib.sha256(
            f"{org_id}|{request.method}|{request.url.path}|{idem_key}|".encode()
            + body
        ).hexdigest()
        cache_key = f"beacon:idem:{digest}"

        cached = await redis.get(cache_key)
        if cached:
            payload = json.loads(cached)
            return JSONResponse(payload["body"], status_code=payload["status"], headers={"X-Idempotent-Replay": "true"})

        # Replay-safe body read for downstream handlers.
        async def receive():  # noqa: ANN202
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = receive  # type: ignore[attr-defined]

        response = await call_next(request)
        # Capture body only for JSON responses with status <500.
        if response.status_code < 500 and response.headers.get("content-type", "").startswith("application/json"):
            resp_body = b""
            async for chunk in response.body_iterator:
                resp_body += chunk
            try:
                parsed = json.loads(resp_body.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                parsed = {"raw": resp_body.decode("utf-8", errors="replace")}
            await redis.set(
                cache_key,
                json.dumps({"status": response.status_code, "body": parsed}),
                ex=TTL_SECONDS,
            )
            return JSONResponse(parsed, status_code=response.status_code, headers=dict(response.headers))
        return response

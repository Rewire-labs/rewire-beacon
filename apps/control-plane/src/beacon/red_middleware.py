"""RED HTTP middleware — records http_requests_total + http_request_duration_seconds.

CORR-2 sweep (2026-05-26): canonical RED middleware adicionado para emit
HTTP_REQUESTS_TOTAL + HTTP_REQUEST_DURATION_SECONDS auto-wired em cada request.
Pattern matching FINOPS canonical RED middleware. Try/except fail-soft.
"""

from __future__ import annotations

import time

from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests served by messaging/beacon control-plane (RED).",
    labelnames=("method", "endpoint", "status_code"),
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds (RED).",
    labelnames=("method", "endpoint"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


class REDMiddleware(BaseHTTPMiddleware):
    """Emit RED metrics (rate, errors, duration) for every HTTP request."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.perf_counter()
        endpoint = request.url.path
        method = request.method

        try:
            response = await call_next(request)
            status_code = str(response.status_code)
        except Exception:
            try:
                HTTP_REQUESTS_TOTAL.labels(
                    method=method, endpoint=endpoint, status_code="500"
                ).inc()
                HTTP_REQUEST_DURATION_SECONDS.labels(
                    method=method, endpoint=endpoint
                ).observe(time.perf_counter() - start)
            except Exception:  # noqa: BLE001
                pass
            raise

        try:
            HTTP_REQUESTS_TOTAL.labels(
                method=method, endpoint=endpoint, status_code=status_code
            ).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method, endpoint=endpoint
            ).observe(time.perf_counter() - start)
        except Exception:  # noqa: BLE001
            pass

        return response


__all__ = ["HTTP_REQUESTS_TOTAL", "HTTP_REQUEST_DURATION_SECONDS", "REDMiddleware"]

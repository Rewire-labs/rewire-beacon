"""RED HTTP middleware — records http_requests_total + http_request_duration_seconds.

RW-MESSAGING-06: fix label schema so PrometheusRule exprs match:
  - added constant label `product="messaging"`
  - renamed `status_code` -> `status` (aligned with PrometheusRule exprs
    and cluster-wide metric convention).

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

# RW-MESSAGING-06: labels aligned with PrometheusRule exprs.
# `product` constant label enables per-product aggregation in alerts.
# `status` (not `status_code`) matches the filter in prometheusrule.yaml.
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests served by rewire-messaging control-plane (RED).",
    labelnames=("method", "endpoint", "status", "product"),
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds (RED).",
    labelnames=("method", "endpoint", "product"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

_PRODUCT = "messaging"


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
            status = str(response.status_code)
        except Exception:
            try:
                HTTP_REQUESTS_TOTAL.labels(
                    method=method, endpoint=endpoint, status="500", product=_PRODUCT
                ).inc()
                HTTP_REQUEST_DURATION_SECONDS.labels(
                    method=method, endpoint=endpoint, product=_PRODUCT
                ).observe(time.perf_counter() - start)
            except Exception:  # noqa: BLE001
                pass
            raise

        try:
            HTTP_REQUESTS_TOTAL.labels(
                method=method, endpoint=endpoint, status=status, product=_PRODUCT
            ).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method, endpoint=endpoint, product=_PRODUCT
            ).observe(time.perf_counter() - start)
        except Exception:  # noqa: BLE001
            pass

        return response


__all__ = ["HTTP_REQUESTS_TOTAL", "HTTP_REQUEST_DURATION_SECONDS", "REDMiddleware"]

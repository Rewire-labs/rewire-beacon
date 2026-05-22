# Multi-stage Dockerfile for BEACON control-plane (V0 skeleton).
# Stage 1 builds a wheel; stage 2 ships a minimal runtime image (non-root).
# context expected: services/rewire-beacon (sub-repo root).
FROM python:3.13-slim AS builder
WORKDIR /build
COPY apps/control-plane/pyproject.toml ./apps/control-plane/pyproject.toml
COPY apps/control-plane/src ./apps/control-plane/src
COPY README.md ./README.md
WORKDIR /build/apps/control-plane
RUN pip install --no-cache-dir --upgrade pip build && python -m build --wheel

FROM python:3.13-slim
ARG APP_VERSION=0.1.0
LABEL org.opencontainers.image.title="rewire-beacon-control-plane" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.vendor="Rewire Labs" \
      org.opencontainers.image.licenses="Proprietary" \
      rewire.io/product="beacon" \
      rewire.io/component="control-plane"
WORKDIR /app
COPY --from=builder /build/apps/control-plane/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm -rf /tmp/*.whl

# Drop privileges per cluster security baseline.
RUN groupadd --gid 65532 nonroot \
 && useradd --uid 65532 --gid 65532 --no-create-home --shell /sbin/nologin nonroot
USER 65532:65532

ENV BEACON_HTTP_HOST=0.0.0.0 \
    BEACON_HTTP_PORT=8080 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys;\
sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=3).status==200 else sys.exit(1)"

ENTRYPOINT ["python", "-m", "uvicorn", "beacon.main:app", "--host", "0.0.0.0", "--port", "8080"]

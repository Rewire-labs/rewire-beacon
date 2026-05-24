# Multi-stage Dockerfile for rewire-notify.
# Stage 1 builds a wheel; stage 2 ships a minimal runtime image.
# Distroless-python is preferred but we keep python:3.11-slim here so
# the operator can run `pip install -e .` locally during development
# (distroless lacks pip).
FROM python:3.11-slim AS builder
WORKDIR /build
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir --upgrade pip build && python -m build --wheel

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm -rf /tmp/*.whl
# Drop privileges per the cluster security baseline.
RUN groupadd --gid 65532 nonroot && useradd --uid 65532 --gid 65532 --no-create-home --shell /sbin/nologin nonroot
USER 65532:65532
EXPOSE 8080
ENV REWIRE_NOTIFY_HTTP_HOST=0.0.0.0 REWIRE_NOTIFY_HTTP_PORT=8080
ENTRYPOINT ["python", "-m", "uvicorn", "rewire_notify.main:app", "--host", "0.0.0.0", "--port", "8080"]

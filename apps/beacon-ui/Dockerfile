# =============================================================================
# beacon-ui — multi-stage Dockerfile (Node 20 builder + nginx-unprivileged)
# =============================================================================

FROM node:20-bookworm-slim AS builder

WORKDIR /build

COPY apps/beacon-ui/package.json apps/beacon-ui/package-lock.json* /build/
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund

COPY apps/beacon-ui/. /build/
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime

COPY --from=builder /build/dist /usr/share/nginx/html
COPY apps/beacon-ui/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:8080/healthz >/dev/null 2>&1 || exit 1

# CORR-D2 (P0-3) — defense-in-depth USER directive canonical (Kyverno require-non-root).
# nginxinc/nginx-unprivileged ja roda como uid 101, USER explicit hardens admission gate.
USER 101

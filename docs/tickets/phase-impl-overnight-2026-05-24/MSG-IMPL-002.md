# MSG-IMPL-002 - Backend stubs (rewire-messaging)

**Owner agente**: Lote 8 sub-lote N
**Estimativa**: 1.5d
**Status**: TODO
**Pre-requisitos**: MSG-IMPL-001 hooks identificam endpoints necessarios

## Definicao

Backend stub funcional rewire-messaging com (escopo: frontend messaging-ui + backend Python email (Resend) + SMS + APNs/FCM + WhatsApp CONNECT):
1. FastAPI app (ou Go/Rust conforme escopo)
2. Endpoints REST per recurso (GET list, GET detail, POST create, PUT update, DELETE)
3. Pydantic models (request + response) com validacao
4. Migrations Alembic per modelo (Postgres CNPG cluster do produto)
5. Auth Authentik OIDC bearer token + tenant isolation (X-Tenant-Id header)
6. Logging structured JSON (compativel Loki ADR 0083)
7. Metricas Prometheus per endpoint (request_count, duration_histogram)
8. OpenAPI spec auto-publicado /docs + /openapi.json
9. Health endpoint /healthz (liveness) + /readyz (readiness checks DB+deps)

## Acceptance criteria

- [ ] FastAPI app boota local (uvicorn) sem erros
- [ ] Endpoints CRUD principais funcionais (mock data inicial OK)
- [ ] Alembic migrations geram schema valido (alembic upgrade head)
- [ ] /docs publica OpenAPI navegavel
- [ ] /healthz + /readyz respondem 200
- [ ] Bearer token check (401 sem token; 200 com mock JWT valido)
- [ ] Tenant isolation: queries WHERE tenant_id = current_tenant
- [ ] Logs JSON estruturados (test grep level info)
- [ ] pyproject.toml dependencies completas

## Referencias

- Gold standard: services/rewire-pulse/apps/pulse-api/src/pulse_api/main.py
- Pattern auth: services/rewire-auth/apps/auth-api/src/middleware/oidc.py
- ADR 0093 (CNPG clusters per produto)
- ADR 0094 (Authentik OIDC 14 clients)
- ADR 0083 (observability metrics canonical V0)

## Notas

Stubs significam endpoints respondem schemas validos com dados mock ou minimal. Logica de negocio real entra em phase seguinte.
Commit PT-BR: feat(rewire-messaging): backend stubs FastAPI endpoints + migrations + OIDC auth (phase-impl-overnight)


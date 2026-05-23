# Architecture — BEACON

## Camadas

```
                   ┌─────────────────────────────────────────┐
   UI (React) ────►│  Kong → AuthMiddleware (JWT/API token)  │
                   │  → TenancyMiddleware (RLS GUC)          │
                   │  → IdempotencyMiddleware (Redis)        │
                   │  → FastAPI router                       │
                   │  → service layer                        │
                   │  → SQLAlchemy async (Postgres CNPG)     │
                   │      └─► RLS POLICY org_isolation       │
                   └────────────────┬────────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
         Kafka topics         Vault/OpenBao         CITADEL chain
   beacon.send.<ch>.<tier>    (creds rotation)     (BLAKE3 anchor)
              │
              ▼
        ┌─────────────────────────────────────────┐
        │ Workers (Kafka consumers)               │
        │  email_sender / sms_sender              │
        │  push_sender / whatsapp_sender          │
        │  → integrations/ (Postal, Zenvia, ...)  │
        │  → emit beacon.events.* to Kafka        │
        └──────────────────┬──────────────────────┘
                           ▼
                  ClickHouse Kafka engine
                           ▼
                beacon_events.messages
                beacon_events.message_events
                beacon_events.daily_stats_by_org_channel (MV)
                           ▲
                           │
                   Analytics endpoints
                   (Redis 5min cache)
```

## Data model split (ADR 0002)

- **Postgres**: tenants/users, domains, templates, suppression list,
  webhooks, push apps, API tokens. RLS FORCE per organization.
- **ClickHouse**: messages + per-event timeline. Particionado por mês.
  TTL 13 meses. Consumido via Kafka engine.

## Multi-tenancy (ADR 0004)

4 camadas:
1. AuthMiddleware resolve identity → `request.state.principal`
2. TenancyMiddleware resolve org_id → `request.state.organization_id`
3. `tenant_scoped_session(org_id)` executa `SET LOCAL beacon.current_org_id`
4. RLS POLICY `org_isolation` filtra todas as queries

Workers usam role `beacon_worker` com BYPASSRLS para varreduras
cross-tenant (analytics, cleanup, billing).

## Auth (ADR 0003)

- UI: Authentik OIDC, JWT validado por JWKS cache 5min, escopos via
  scope claim
- SDK: API tokens `bcn_live_<32 chars>` armazenados como HMAC-SHA256
  (deterministic lookup), prefix indexado, suporta scopes + expiração +
  revogação

## Auth chain (ADR 0005)

Por mensagem: hash BLAKE3(org|recipient|channel|content_digest|ts|consent_basis).
Hash salvo na linha de notification + anchor async para CITADEL via
POST /chain/append (fire-and-forget; falha não bloqueia envio).

## Compliance

- LGPD Art. 18: `POST /v1/audit/lgpd/dsar` enfileira background job que
  agrega dados de Postgres + ClickHouse + suppression list → JSON.
- LGPD Art. 48: `POST /v1/audit/lgpd/breach-notify` registra incidente
  com deadline ANPD calculado (3 dias).
- Lawful basis obrigatório em todo send (Pydantic Literal enforce).
- Cross-canal unsubscribe via `/v1/u/<token>` HMAC-signed.

## Anti-spam (BCN-110)

Pre-send heuristic <50ms:
- Keyword match em SPAM_KEYWORDS
- Excessive caps / URL count
- Tenant tenure × volume burst
- Recent bounce rate

Score >= 60 = block + alerta customer success.
Score 30-59 = review (não bloqueia).

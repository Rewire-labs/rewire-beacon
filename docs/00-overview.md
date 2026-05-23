# BEACON — Overview

BEACON é a plataforma de notificações multi-canal BR da Rewire: email
(Postal + SES sa-east-1 fallback), SMS (Zenvia + TotalVoice), push
mobile (APNs + FCM), push web (VAPID) e WhatsApp (via CONNECT). Pricing
em real, NF-e automática, audit chain BLAKE3 + LGPD nativo.

## Stack

- Control-plane: FastAPI 0.115+ (Python 3.13) — `apps/control-plane/`
- UI: Vite + React 19 + TypeScript — `apps/beacon-ui/`
- Persistência: PostgreSQL 17 (CNPG compartilhado) + ClickHouse 24.x
  para eventos analytics + Redis 7.4 cache/idempotency
- Brokers: Redpanda/Strimzi Kafka — tópicos `beacon.send.*` (workers
  consomem) e `beacon.events.*` (ClickHouse Kafka engine consome)
- Workflows: Temporal 1.25+ — `MultiChannelJourneyWorkflow`
- Identity: Authentik OIDC (UI) + API tokens HMAC-SHA256 (SDK)
- Secrets: OpenBao/Vault via ESO operator
- Auth chain: BLAKE3 (sha3-256 fallback) + CITADEL anchor async

## Layout

```
apps/
  control-plane/        FastAPI service, Alembic migrations, workers
    src/beacon/
      api/              HTTP routers (messages, domains, suppression, ...)
      services/         business logic (messaging, antispam, pricing)
      workers/          Kafka consumers + cron jobs
      integrations/     external clients (Postal, Zenvia, APNs, ...)
      middleware/       auth + tenancy (RLS GUC) + idempotency
      db/               SQLAlchemy models + async session factories
      workflows/        Temporal workflow defs
      clickhouse_schema.sql
  beacon-ui/            React SPA, mock+API hybrid via @/lib/api
cluster/                Kubernetes manifests (ESO, NetworkPolicy, Kong)
docs/
  adr/                  Architecture Decision Records
  tickets/              Sprint backlog (BCN-XXX)
  runbooks/             Operational guides
tests/                  pytest (unit + RLS + smoke)
```

## Quickstart dev

```bash
cd apps/control-plane
pip install -e ".[dev]"
alembic upgrade head
uvicorn beacon.main:app --reload --port 8080
# Hit http://localhost:8080/docs
```

UI:

```bash
cd apps/beacon-ui
npm install
VITE_BEACON_API_BASE=http://localhost:8080/v1 npm run dev
```

## Status implementação

V0.3 — todos os canais funcionais, anti-spam ML, LGPD DSAR + breach
notification, Lago billing + NFe.io + Asaas. ClickHouse analytics +
Temporal journeys + WhatsApp via CONNECT prontos para integração quando
serviços externos GA.

Tickets: ver `docs/tickets/README.md` (~150 IDs BCN-XXX).

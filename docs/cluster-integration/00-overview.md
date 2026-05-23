# Cluster integration — Overview

BEACON roda no cluster Rewire em namespace `beacon`. Componentes:

| Componente | Tipo K8s | Replicas | Recursos |
|---|---|---|---|
| `beacon-control-plane` | Deployment | 3 | 500m CPU, 1Gi RAM |
| `beacon-email-sender-{hobby,starter,scale,enterprise}` | Deployment | 2 cada | 200m, 512Mi |
| `beacon-sms-sender-{tier}` | Deployment | 1 cada | 100m, 256Mi |
| `beacon-push-sender-{ios,android,web}-{tier}` | Deployment | 1 cada | 100m, 256Mi |
| `beacon-whatsapp-sender-{tier}` | Deployment | 1 cada | 100m, 256Mi |
| `beacon-usage-reporter` | CronJob 5min | - | 50m, 128Mi |
| `beacon-bad-token-cleanup` | CronJob 15min | - | 50m, 128Mi |
| `beacon-template-sync` | CronJob 15min | - | 50m, 128Mi |
| `beacon-ui` | Deployment | 2 | 100m, 128Mi |

## Dependências externas (cross-product)

- **Postgres CNPG `rewire-shared`** (namespace `postgres-system`) — schema `beacon`
- **Redis** (namespace `redis`) — DB 0
- **Redpanda/Kafka** (namespace `redpanda`) — topics `beacon.*`
- **ClickHouse** (namespace `clickhouse`) — database `beacon_events`
- **Temporal** (namespace `temporal`) — task queue `beacon-journeys`
- **Vault/OpenBao** (namespace `vault`) — paths `secret/rewire/beacon/*`
- **MinIO** (namespace `minio`) — buckets `beacon-evidence`, `beacon-templates-assets`
- **Kong** (namespace `kong`) — Ingress
- **CONNECT** (namespace `connect`) — WhatsApp delegation
- **CITADEL** (namespace `rewire-citadel`) — audit chain anchor

## DNS

- `api.beacon.rewirelabs.dev` — REST API (Kong → beacon-control-plane:8080)
- `app.beacon.rewirelabs.dev` — UI (Kong → beacon-ui:80)
- `track.beacon.rewirelabs.dev` — open/click tracking redirector (V0.4+)

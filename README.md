# rewire-messaging

> **Plataforma BR de notificações transacionais multi-canal — Email + SMS + Push (iOS/Android) + WhatsApp (V0.3 via rewire-connect) + Telegram interno.**
> Umbrella pós-ADR 0108 §C2 (consolida `rewire-notify` + `rewire-beacon`).
> Status: **V0 done 20/20 binário verde** (Slot 4 Run 4 — 2026-05-25) + CORR-2 RED middleware + CORR-3 service port 8080 alignment (2026-05-26).
> Owner: Cluster team + comercial · GitHub: `Rewire-labs/rewire-messaging` (renomeado de `rewire-beacon`).

**Canonical spec autoritativa**: [`CANONICAL_DOC.md`](./CANONICAL_DOC.md).

## What it does

API única BR umbrella para envio multi-canal de notificações transacionais e marketing-light:

- **Email transacional** — Postal 3.x self-hosted (MIT) primário + Resend (US, fallback automático) com circuit breaker 3-fail-30s per-provider
- **SMS BR** — Zenvia (parceria revenue-share); E.164 validation `+55<DDD><8/9 digits>`
- **Push iOS** — APNs HTTP/2 + token p8 (direto Apple)
- **Push Android** — FCM v1 + service account OAuth (direto Google)
- **Push Web** — `410 Gone V0` (Sunset → V0.3 VAPID + Service Worker RFC 8030)
- **WhatsApp** — backlog V0.3 (delegação para `rewire-connect` internal API)
- **Telegram interno** — `@RewireLabsBot` ops notifications (cluster team)
- **Templates per-tenant** (MJML/Handlebars), **webhooks inbound** providers, **DSAR LGPD endpoints**, **CITADEL audit chain anchors**

Diferencial: **uma API + UI + billing único + NF-e + audit chain BLAKE3 + LGPD nativo cross-canal**, pricing 40-60% abaixo SendGrid/Twilio/OneSignal BR.

## Arquitetura V0

```
clientes (todos produtos Rewire + apps externos)
    │ REST + SDK (Py/TS)
    v
┌──────────────────────────────────────────────────────────────┐
│ Kong ingress (rate-limit + oidc-authentik + correlation-id)   │
│   messaging.rewirelabs.dev  (alias: beacon.rewirelabs.dev/90d)│
└────────────────────────────┬─────────────────────────────────┘
                             v
┌──────────────────────────────────────────────────────────────┐
│ control-plane FastAPI 0.115 / Python 3.13 / port 8080         │
│  /healthz /ready /metrics  (RED middleware CORR-2)            │
│  /v1/emails  /v1/sms  /v1/push  /v1/templates                 │
│  /v1/webhooks/{postal|resend|zenvia|apns|fcm}                 │
│  /v1/notifications (legacy umbrella /90d)                     │
│  /v1/lgpd/{dsar,export,delete}                                │
└─────┬──────────┬──────────────┬──────────────┬───────────────┘
      v          v              v              v
  Email rtr  SMS rtr        Push rtr      Webhook normalizer
  Postal→Resend Zenvia      APNs+FCM     (HMAC verify per-provider)
  (CB)        (CB)          (CB)
                             │
                             v
  pgmq queues (msg_outbound + msg_retry + msg_dlq) — Postgres 17
                             │
                             v
  Postgres CNPG 17 (RLS FORCE) · Redis · Vault · Authentik OIDC
  CITADEL anchor (BLAKE3) · Lago emit · AUDIT evidence
```

Detalhes completos: [`CANONICAL_DOC.md §3`](./CANONICAL_DOC.md#3-arquitetura).

## Cross-product (nomes canonical pós-ADR 0108)

| Produto | Integração |
|---|---|
| **rewire-app / admin / deploy / sentinel / pulse / finops / audit / security / foundry / customer-support / servers / ascend / databases / tenant-metering** | Emitters — todos enviam via messaging |
| **rewire-connect** | Provê adapter WhatsApp BSP (messaging POST `/connect/internal/v1/whatsapp/send`) — V0.3 |
| **rewire-citadel** | BLAKE3 hash anchor por mensagem |
| **rewire-audit** | Compliance evidence emission (DSAR ready) |
| **rewire-tenant-metering** | Plan tier lookup + Lago billable counters |
| **Authentik / Vault / Postgres CNPG / PULSE / Lago** | Infra backbone |

## Quickstart (dev local)

Requisitos: Python 3.13 + uv (recomendado) ou pip.

```bash
cd apps/control-plane
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

cp ../../.env.example .env
export $(cat .env | xargs)

uvicorn beacon.main:app --host 0.0.0.0 --port 8080 --reload

curl http://localhost:8080/healthz
# {"status":"ok","service":"rewire-messaging","version":"0.2.0"}

curl http://localhost:8080/openapi.json | jq '.info'
```

OpenAPI 3.1 spec exposta em `/openapi.json` (FastAPI auto-gen). Para dump estático: `python scripts/dump_openapi.py > docs/api/openapi.yaml`.

## Smoke tests

```bash
# 7 sections, 13 assertions cobrindo health/email/sms/push/templates/webhooks/tenant guard
./tests/smoke.sh
```

## Lint / type / test

```bash
ruff check apps/control-plane/src
mypy apps/control-plane/src
pytest -q
# 45/45 tests passed — 83% cov em messaging_cp.*
```

## Container build

```bash
docker build -f apps/control-plane/Dockerfile -t rewire-messaging-control-plane:dev .
docker run --rm -p 8080:8080 \
  --env-file .env \
  rewire-messaging-control-plane:dev
```

Dockerfile expõe **port 8080** (canonical pós-CORR-3); container roda non-root user 65532 + read-only rootfs.

## CI/CD

- **Gitea workflow** (`.gitea/workflows/publish.yml`) — V0 active, push para registry in-cluster:
  `192.168.1.110:30500/rewire-labs/rewire-messaging-control-plane:{dev-latest, sha-long, sha-short, version}`
- **GitHub mirror** (`.github/workflows/build.yml`) → `ghcr.io/rewire-labs/rewire-messaging-control-plane`
- **CI** (`.github/workflows/ci.yml`) — ruff + mypy + pytest

ArgoCD deploya via `argocd/applicationsets/products.yaml` (entry `rewire-messaging`) usando chart canonical em `architecture/products/messaging/helm/` + `clusters/prod/values-messaging.yaml`.

## Canonical paths

| Item | Path |
|---|---|
| Canonical spec | [`CANONICAL_DOC.md`](./CANONICAL_DOC.md) |
| Helm chart canonical | `architecture/products/messaging/helm/` |
| API contract | `docs/products/messaging/API_CONTRACT.md` |
| LGPD compliance | `docs/products/messaging/LGPD.md` |
| Canonical namespace | `apps/control-plane/src/messaging_cp/` |
| Legacy namespace (90d sunset) | `apps/control-plane/src/beacon/` |
| Email adapters (Postal + Resend + CB router) | `messaging_cp/adapters/email/{postal,resend,router}.py` |
| SMS adapter (Zenvia + router) | `messaging_cp/adapters/sms/{zenvia,router}.py` |
| Push adapters (APNs + FCM + router) | `messaging_cp/adapters/push/{apns,fcm,router}.py` |
| pgmq queues + workers | `messaging_cp/queues/{sender_worker,retry_worker}.py` |
| Credits + Lago emit | `messaging_cp/{credits_emit,lago_emit}.py` |
| pgmq migration | `apps/control-plane/migrations/versions/0005_pgmq_queues.py` |
| RED middleware (CORR-2) | `apps/control-plane/src/beacon/red_middleware.py` |
| Audit chain (BLAKE3 + CITADEL) | `apps/control-plane/src/beacon/services/audit_chain.py` |
| Resend client | `apps/control-plane/src/beacon/integrations/resend.py` |
| Python SDK | `sdk/python/messaging/__init__.py` |
| TypeScript SDK | `sdk/typescript/src/index.ts` |
| MSW frontend mocks | `apps/beacon-ui/src/mocks/{handlers,browser}.ts` |
| Smoke battery | `tests/smoke.sh` |
| Authentik blueprint | `architecture/identity/authentik-blueprints/10-providers/provider-rewire-messaging.yaml` |
| Lago metrics | `architecture/lago/billable_metrics_canonical.yaml` (linhas 168-215) |

## Provider routing matrix

| Canal | Primário | Fallback | Circuit Breaker |
|---|---|---|---|
| Email | Postal (self-hosted) | Resend (US) | per-provider, 3-fail-30s |
| SMS BR | Zenvia | (V0.1: SNS/Twilio) | per-provider |
| Push iOS | APNs (HTTP/2, p8 token) | n/a (single) | per-provider |
| Push Android | FCM v1 (SA OAuth) | n/a (single) | per-provider |
| Push Web | **410 Gone V0** (V0.3 VAPID) | n/a | n/a |
| WhatsApp | V0.3 via rewire-connect | n/a | n/a |

## Credits + Lago

| Action | Weight | Lago metric |
|---|---|---|
| `email_transactional` | 0 | `messaging_email_sent` |
| `sms_br` | 2 | `messaging_sms_sent` |
| `push_notification` | 0 | `messaging_push_sent` |

Lago aggregator `messaging_credits_consumed` (sum recurring) carrega o wallet impact final. V0: **email + push free**, **SMS billable BR pass-through** (~R$ 0,10/SMS).

## Auth + Vault paths

OIDC issuer: `https://auth.rewirelabs.dev/application/o/messaging/` (client_id `messaging`).
Scopes: `messaging:send` · `messaging:read` · `messaging:admin` · `messaging:dsar`.

Vault paths (ESO `ClusterSecretStore name=vault-kv`, refresh 30min):

- `kv/rewire-messaging/{database, redis, rabbitmq, oidc, postal, resend-api-key, zenvia, telegram-*}`
- Per-tenant: `secret/data/rewire/messaging/{tenant}/{postal/<domain>/dkim, ses/credentials, zenvia/api-token, apns/<bundle_id>/cert, fcm/<project_id>/key, vapid/<origin>/keypair}`

Migration legacy paths ex-notify+ex-beacon: `docs/runbooks/vault-path-migration-messaging.md`.

## LGPD

- **Lawful basis matrix** (Art. 7) — `docs/products/messaging/LGPD.md`
- **DSAR endpoints**: `/v1/lgpd/{dsar, export, delete, correct}` — SLA 15 dias
- **Retention**: message body 90d · metadata 5y · suppression permanente · CITADEL chain 10y
- **Transfers** (Art. 33): Resend/APNs/FCM US-hosted (execução de contrato Art. 33-IX); Postal+Zenvia BR sem transfer
- **Special categories** (Art. 11): credenciais/saúde/biométricos **NÃO aceitos** (tenant deve filtrar upstream)

## Observability

- Prometheus `/metrics` (port 8080, scrape 30s via ServiceMonitor)
- RED middleware: `http_requests_total` + `http_request_duration_seconds`
- Domain metrics: `messaging_dispatch_total`, `messaging_webhook_events_total`, `messaging_circuit_breaker_state`, `messaging_pgmq_queue_depth`
- PrometheusRule alerts: HighErrorRate (5xx >5% 5min), HighLatency (p99 >2s 10min), BurnRate (SLO 99.9% multi-window), ProviderCBOpen (>5min), DLQGrowing (>100), Saturation (CPU >80% 15min)
- OTLP traces: `MESSAGING_OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.observability.svc.cluster.local:4317`
- Logs: structlog JSON com `tenant_id`, `trace_id`, `request_id`; PII redacted (emails/phones hashed)

## Roadmap

| Versão | Escopo |
|---|---|
| V0.1 (unblock) | Build + push imagem `dev-latest` registry + redeploy (P0 sistêmico atual) |
| V0.2 | Postal MTA pool warm-up + AWS SES fallback + APNs/FCM production load + MJML render service |
| V0.3 | WhatsApp via rewire-connect + VAPID Web Push + DSAR correct/suppression bulk |
| V0.4 | ClickHouse analytics + Temporal journeys multi-step + anti-spam ML + Kafka→pgmq full |
| V0.5 | A/B testing + UI Lovable (19 telas rework) + billing Lago wire + NF-e Asaas |
| V0.6 | DSAR full + suppression cross-canal unified |
| V1 | Stalwart alternativa Postal + voice calling BSP + ICP-Brasil sign |

Detalhes em [`CANONICAL_DOC.md §12`](./CANONICAL_DOC.md#12-roadmap).

## Legacy code (preservado)

- `legacy/notify/` — código original `rewire-notify` preservado pós-merge ADR 0108 §C2
- `BEACON.md` — spec autoritativa beacon V0 (push + SMS) — referência histórica 1008 linhas
- `apps/control-plane/src/beacon/` — namespace legacy co-mounted em `/v1` /90d sunset

## License

Proprietary — Rewire Labs.

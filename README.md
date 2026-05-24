# rewire-messaging

> **Status**: V0 skeleton (consolidacao pos-ADR 0108 secao C2) — umbrella todos canais (email + SMS + push mobile/web + WhatsApp via CONNECT)
> **Consolidacao ADR 0108 C2**: funde `rewire-notify` (email transactional) + `rewire-beacon` (push mobile/web APNs/FCM/VAPID + SMS) em UM produto umbrella. PME ve "um lugar pra avisar cliente", reduz surface area.
> **Telas Lovable**: 19 (herdadas de beacon)
> **GitHub origem**: `Rewire-labs/rewire-messaging` (renomeado de `rewire-beacon`)
> Owner: cluster team + comercial

## What it does (V0 scope)

API unica BR umbrella para envio multi-canal:
- **Email transactional** (Postal self-hosted + AWS SES sa-east-1 fallback) — ex-rewire-notify V0.1
- **SMS** (Zenvia + TotalVoice via API parceiros) — V0.2
- **WhatsApp** (delegado para rewire-connect API interna) — depende de connect GA
- **Push mobile** (APNs Apple + FCM Google diretos, sem intermediario) — V0.2
- **Push web** (VAPID + Web Push RFC 8030) — V0.3
- **Journeys multi-step** (Temporal workflows: email + se nao abrir 24h, SMS + se nao responder 48h, WhatsApp) — V0.4
- **A/B test + segmentacao** — V0.5
- **Suppression list cross-canal** (opt-out email vale SMS/WA/push) — V0.6

Diferencial absoluto: **uma API unica + UI unica + billing unico + NF-e + audit chain BLAKE3 (rewire-citadel) + LGPD nativo cross-canal**.

Este repo entrega o V0 **scaffolding** apenas: control-plane FastAPI com endpoints stub retornando `{"status":"not_implemented","todo":"V0.2"}` exceto `/healthz` `/ready` `/metrics` que sao funcionais.

## Architecture (V0)

```
clientes (apps/sites/backends/todos produtos Rewire emitters)
    | REST API + SDK
    v
+-----------------------------------------------------------------------+
| rewire-messaging control-plane (FastAPI 0.115 / Python 3.13)          |
|   |- /healthz /ready /metrics            (V0 functional)              |
|   |- /v1/notifications  (send)           (V0 stub)                    |
|   |- /v1/channels       (list)           (V0 stub)                    |
|   |- /v1/templates      (CRUD)           (V0 stub)                    |
|   |- /v1/deliveries     (status)         (V0 stub)                    |
|   |- /v1/journeys       (multi-step)     (V0 stub)                    |
|   |- /v1/ab-tests       (variant flow)   (V0 stub)                    |
|   |- /v1/segments       (audience)       (V0 stub)                    |
|   `- /v1/webhooks/{provider}             (V0 stub — Postal/Zenvia)    |
+-----------------------------------------------------------------------+
| Postgres 17 (transactional)  Redis 7.4 (quota/rate)                   |
| RabbitMQ 4.x (retry / DLQ)   Kafka (Strimzi) topic per channel/tier   |
| ClickHouse 24.x (events)     Temporal 1.25 (multi-step journeys)      |
| Vault (OpenBao) secrets      Authentik OIDC + tenant API tokens       |
+-----------------------------------------------------------------------+
```

Roadmap futuro (nao V0):
- workers (email/sms/push/wa fan-out)
- anti-spam ML (scikit-learn + sentence-transformers)
- MJML template render service
- ClickHouse ingest + analytics queries
- Temporal worker (multi-channel journeys)
- UI (Lovable + React — 19 telas herdadas beacon)

## Cross-product (nomes canonical pos-ADR 0108)

| Produto | Integracao messaging |
|---|---|
| **TODOS produtos do ecossistema** | enviam notifications via rewire-messaging (transactional/marketing/system) |
| **rewire-connect** | provê adapter WhatsApp Business (messaging envia WA via `POST /connect/internal/v1/whatsapp/send`) |
| **rewire-citadel** (ex-citadel-cloud) | cada mensagem tem hash BLAKE3 anchored na audit chain |
| **rewire-audit** (ex-audit-trail) | mensagens fluem como compliance evidence (DSAR ready) |
| **rewire-security** (ex-guardian+phalanx) | detect emite alerts severity=critical via messaging multi-canal |
| **rewire-foundry** | golden paths geram codigo que usa rewire-messaging SDK |
| **rewire-servers** (ex-host) | apps em VMs recebem rewire-messaging SDK pre-instalado |
| **rewire-customer-support** | ticket notifications (criacao/update/resolve) via rewire-messaging |
| **rewire-pulse** (ex-pulse-cloud) | OTLP + anomaly markers de delivery failures |
| **rewire-finops** (ex-cloudx) | budget alerts + recomendacoes via email |
| **rewire-deploy** | deploy notifications + rollback alerts |
| **rewire-sentinel** | test failure notifications |

## Dev quickstart

```bash
# requires Python 3.13 + uv (recomendado) ou pip
cd apps/control-plane
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

cp ../../.env.example .env
export $(cat .env | xargs)

uvicorn messaging.main:app --host 0.0.0.0 --port 8080 --reload

curl http://localhost:8080/healthz
# {"status":"ok","service":"rewire-messaging","version":"0.1.0"}
```

## Lint / test

```bash
ruff check apps/control-plane/src
mypy apps/control-plane/src
pytest -q
```

## Container build (local)

```bash
docker build -f apps/control-plane/Dockerfile -t rewire-messaging-control-plane:dev .
docker run --rm -p 8080:8080 rewire-messaging-control-plane:dev
```

## CI/CD

- `.gitea/workflows/publish.yml` — V0 active, pushes para registry in-cluster
  `192.168.1.110:30500/rewire-labs/rewire-messaging-control-plane:{dev-latest, sha-long, sha-short, version}`
- `.github/workflows/build.yml` — mirror para `ghcr.io/rewire-labs/rewire-messaging-control-plane`
- `.github/workflows/ci.yml` — ruff + mypy + pytest

ArgoCD deploya via `clusters/prod/values-messaging.yaml` + chart canonical em
`architecture/products/messaging/helm/`.

## Legacy code (preservado)

- `legacy/notify/` — codigo original `rewire-notify` (email transactional) preservado pos-merge ADR 0108 C2
- `BEACON.md` — spec autoritativa beacon V0 (push + SMS) preservada como referencia historica

## Vault paths (canonical pos-ADR 0108)

- `secret/rewire/messaging/{tenant}/postal/{domain}/dkim` (ex-`secret/rewire/notify/...`)
- `secret/rewire/messaging/{tenant}/ses/credentials`
- `secret/rewire/messaging/{tenant}/zenvia/api-token`
- `secret/rewire/messaging/{tenant}/apns/{bundle_id}/cert`
- `secret/rewire/messaging/{tenant}/fcm/{project_id}/key`
- `secret/rewire/messaging/{tenant}/vapid/{origin}/keypair`

Ver `docs/runbooks/vault-path-migration-messaging.md` para procedimento migration paths ex-notify+ex-beacon -> messaging.

## V0 -> V0.2+ TODOs

- [ ] V0.2: Postal MTA pool + AWS SES fallback wired no email worker
- [ ] V0.2: Zenvia/TotalVoice clients no SMS worker
- [ ] V0.2: APNs (aioapns) + FCM (google-cloud-firebase) clients no push worker
- [ ] V0.3: WhatsApp worker chamando rewire-connect internal API
- [ ] V0.3: Template render MJML + Handlebars
- [ ] V0.3: ClickHouse ingest + analytics queries
- [ ] V0.4: Temporal worker journeys multi-step
- [ ] V0.4: Anti-spam ML pipeline (scikit-learn)
- [ ] V0.5: UI (React — 19 telas Lovable herdadas beacon) + billing (Lago + Asaas) + NF-e
- [ ] V0.5: A/B test + segmentacao audiences
- [ ] V0.6: DSAR endpoints (LGPD) + suppression list cross-canal
- [ ] V1: Stalwart Mail Server alternativa para Postal

## License

Proprietary — Rewire Labs.

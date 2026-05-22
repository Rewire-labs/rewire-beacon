# rewire-beacon

> Notification platform multi-canal BR (email + SMS + WhatsApp + push mobile + push web)
>
> Status: V0 skeleton (control-plane + canonical scaffolding only — sem implementacao real dos canais)
> Spec: `docs/futuros_produtos/futuros_produtos.md` secao 2 (BEACON)
> Owner: cluster team + comercial

## What it does (V0 scope)

API unica BR para envio transacional:
- Email (Postal self-hosted + AWS SES sa-east-1 fallback) — V0.1
- SMS (Zenvia + TotalVoice via API parceiros) — V0.2
- WhatsApp (delegado para CONNECT API interna) — depende de CONNECT GA
- Push mobile (APNs + FCM diretos, sem intermediario) — V0.2
- Push web (VAPID + Web Push RFC 8030) — V0.3

Diferencial absoluto: **uma API unica + UI unica + billing unico + NF-e + audit chain
BLAKE3 (CITADEL) + LGPD nativo cross-canal**.

Este repo entrega o V0 **scaffolding** apenas: control-plane FastAPI com endpoints stub
retornando `{"status":"not_implemented","todo":"V0.2"}` exceto `/healthz` `/ready`
`/metrics` que sao funcionais.

## Architecture (V0)

```
clientes (apps/sites/backends)
    │ REST API + SDK
    ▼
┌───────────────────────────────────────────────────────────────────────┐
│ BEACON control-plane (FastAPI 0.115 / Python 3.13)                    │
│   ├─ /healthz /ready /metrics            (V0 functional)              │
│   ├─ /v1/notifications  (send)           (V0 stub)                    │
│   ├─ /v1/channels       (list)           (V0 stub)                    │
│   ├─ /v1/templates      (CRUD)           (V0 stub)                    │
│   ├─ /v1/deliveries     (status)         (V0 stub)                    │
│   └─ /v1/webhooks/{provider}             (V0 stub — Postal/Zenvia)    │
├───────────────────────────────────────────────────────────────────────┤
│ Postgres 17 (transactional)  Redis 7.4 (quota/rate)                   │
│ RabbitMQ 4.x (retry / DLQ)   Kafka (Strimzi) topic per channel/tier   │
│ ClickHouse 24.x (events)     Temporal 1.25 (multi-step journeys)      │
│ Vault (OpenBao) secrets      Authentik OIDC + tenant API tokens       │
└───────────────────────────────────────────────────────────────────────┘
```

Roadmap futuro (nao V0):
- workers (email/sms/push/wa fan-out)
- anti-spam ML (scikit-learn + sentence-transformers)
- MJML template render service
- ClickHouse ingest + analytics queries
- Temporal worker (multi-channel journeys)
- UI (Lovable + React)

Veja `docs/futuros_produtos/futuros_produtos.md` secao 2.11 para diagrama completo.

## Dev quickstart

```bash
# requires Python 3.13 + uv (recomendado) ou pip
cd apps/control-plane
uv venv && source .venv/bin/activate  # or `python -m venv .venv`
uv pip install -e ".[dev]"            # or `pip install -e ".[dev]"`

# minimal env (booting against in-memory Postgres-like — SQLite fallback OK no V0)
cp ../../.env.example .env
export $(cat .env | xargs)

# boot dev
uvicorn beacon.main:app --host 0.0.0.0 --port 8080 --reload

# probe healthz
curl http://localhost:8080/healthz
# {"status":"ok","service":"rewire-beacon","version":"0.1.0"}
```

## Lint / test

```bash
ruff check apps/control-plane/src
mypy apps/control-plane/src
pytest -q
```

## Container build (local)

```bash
docker build -f apps/control-plane/Dockerfile -t rewire-beacon-control-plane:dev .
docker run --rm -p 8080:8080 rewire-beacon-control-plane:dev
```

## CI/CD

- `.gitea/workflows/publish.yml` — V0 active, pushes para registry in-cluster
  `192.168.1.110:30500/rewire-labs/rewire-beacon-control-plane:{dev-latest, sha-long, sha-short, version}`
- `.github/workflows/build.yml` — mirror para `ghcr.io/rewire-labs/rewire-beacon-control-plane`
- `.github/workflows/ci.yml` — ruff + mypy + pytest

ArgoCD deploya via `clusters/prod/values-beacon.yaml` + chart canonical em
`architecture/products/beacon/helm/`.

## Cross-product integrations

| Produto | Integracao BEACON |
|---|---|
| **CONNECT** | BEACON delega envio WhatsApp via `POST /connect/internal/v1/whatsapp/send` |
| **CITADEL** | cada mensagem tem hash BLAKE3 anchored na audit chain |
| **AUDIT TRAIL** | mensagens fluem como compliance evidence |
| **GUARDIAN** | alertas severity=critical sao enviados via BEACON multi-canal |
| **FOUNDRY** | golden paths geram codigo que usa BEACON SDK |
| **HOST** | apps em VMs HOST recebem BEACON SDK pre-instalado |
| **SUPPORT** | ticket notifications (criacao/update/resolve) via BEACON |

## V0 → V0.2+ TODOs

- [ ] V0.2: Postal MTA pool + AWS SES fallback wired no email worker
- [ ] V0.2: Zenvia/TotalVoice clients no SMS worker
- [ ] V0.2: APNs (aioapns) + FCM (google-cloud-firebase) clients no push worker
- [ ] V0.3: WhatsApp worker chamando CONNECT internal API
- [ ] V0.3: Template render MJML + Handlebars
- [ ] V0.3: ClickHouse ingest + analytics queries
- [ ] V0.4: Temporal worker journeys multi-step
- [ ] V0.4: Anti-spam ML pipeline (scikit-learn)
- [ ] V0.5: UI (React) + billing (Lago + Asaas) + NF-e
- [ ] V0.6: DSAR endpoints (LGPD) + suppression list cross-canal
- [ ] V1: Stalwart Mail Server alternativa para Postal

## License

Proprietary — Rewire Labs.

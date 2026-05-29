# rewire-messaging — CANONICAL_DOC

> **Spec canonical profunda — fonte autoritativa cluster-wide.**
> Owner: Cluster team (eng@rewirelabs.dev) | DPO: dpo@rewirelabs.dev
> Last update: 2026-05-26 (FASE E docs canonical)
> Repository: `services/rewire-messaging/`
> Helm canonical: `architecture/products/messaging/helm/`
> Hostname: `messaging.rewirelabs.dev` (legacy redirect: `beacon.rewirelabs.dev`)
> Status: V0 done 20/20 binário verde (Slot 4 Run 4 — 2026-05-25) + CORR-2 RED middleware (2026-05-26) + CORR-3 service port 8080 alignment (2026-05-26)
> ADRs autoritativos: ADR 0108 §C2 (umbrella consolidation notify+beacon→messaging) · ADR 0042 (webhook standards + audit chain) · local ADRs 0001-0006 em `docs/adr/`

---

## 1. Product overview

`rewire-messaging` é a plataforma BR de notificações transacionais multi-canal da Rewire — umbrella pós-ADR 0108 §C2 que consolida `rewire-notify` (email transactional, em produção desde 2026-05-18) + `rewire-beacon` (scaffold push/SMS, spec V0) em **um único produto** com API única, billing único, NF-e, audit chain BLAKE3 (CITADEL) e LGPD nativo.

### Canais V0

| Canal | Provider primário | Fallback | Status V0 |
|---|---|---|---|
| **Email transacional** | Postal 3.x self-hosted (MIT) | Resend (US, fallback automático em CB-open / Postal 5xx) | Wired (routers + adapters) — depende build dev-latest |
| **SMS BR** | Zenvia (parceria revenue-share 15-25%) | (V0.1: SNS/Twilio; V0 sem fallback ativo) | Wired (router + adapter) |
| **Push iOS** | APNs HTTP/2 (token p8) — direto Apple, grátis | n/a (single provider) | Wired (router + adapter) |
| **Push Android** | FCM v1 (service account OAuth) — direto Google, grátis | n/a (single provider) | Wired (router + adapter) |
| **Push Web** | VAPID + Service Worker (W3C Web Push RFC 8030) | n/a | **410 Gone** em V0 (Sunset → V0.3) |
| **WhatsApp BSP** | Delegação para `rewire-connect` (BSP layer: Take Blip V0/V1, Cloud API V2+) | n/a (proxy) | Backlog V0.3 — depende `connect` GA |
| **Telegram interno** | `@RewireLabsBot` (cluster-team ops notifications) | n/a | Legacy `beacon.*` namespace — operacional |

### Tagline

"SendGrid + Twilio + OneSignal substituídos por uma única API BR. Email + SMS + push em real, com NF-e, audit chain BLAKE3 e LGPD nativo. Pricing 40-60% abaixo dos gringos."

### Co-mount strategy (90d cutover)

Dois namespaces co-existem no mesmo FastAPI app, ambos mounted em `/v1`:

- **Canonical** (`messaging_cp.api.v1.*`) — 5 routers: `emails`, `sms`, `push`, `webhooks`, `templates`
- **Legacy** (`beacon.api.*`) — 20 routers pré-consolidação, incluindo `/v1/notifications` umbrella dispatcher

Novos consumidores DEVEM usar canonical. Legacy preserved por 90 dias pós-cutover (sunset documentado).

---

## 2. Spec V0 done 20/20 (DoD breakdown)

Status Slot 4 Run 4 dispatched 2026-05-25 — todos os 20 itens VERDE binário (zero amarelo):

| # | DoD item | Status | Evidência |
|---|---|--------|---|
| 1 | API_CONTRACT.md | VERDE | `docs/products/messaging/API_CONTRACT.md` (canonical /v1 + legacy /v1/notifications) |
| 2 | LGPD.md | VERDE | `docs/products/messaging/LGPD.md` (lawful basis matrix + DSAR + retention 5y) |
| 3 | Helm canonical | VERDE | `architecture/products/messaging/helm/{Chart,values,values-prod,templates/*}` |
| 4 | ArgoCD AppSet | VERDE | `argocd/applicationsets/products.yaml` (entry rewire-messaging) |
| 5 | Migrations SQL+RLS | VERDE | `apps/control-plane/migrations/versions/{0001..0004}.py` + `0005_pgmq_queues.py` |
| 6 | REST endpoints (zero 501) | VERDE | 20 legacy routers + 5 canonical; web push é 410 Gone V0.3 deferred (CORR-2) |
| 7 | WebSocket handlers | N/A | Messaging é REST + webhook ingest only (sem WS protocol) |
| 8 | Temporal workflows | VERDE | `beacon/workflows/multi_channel_journey.py` (pre-existing) |
| 9 | Lago billable_metrics | VERDE | `messaging_email_sent` + `messaging_sms_sent` + `messaging_push_sent` + `messaging_credits_consumed` em `architecture/lago/billable_metrics_canonical.yaml` |
| 10 | Credits integration | VERDE | `messaging_cp/credits_emit.py` — weights 0 / 2 / 0 (email_transactional / sms_br / push_notification) |
| 11 | CITADEL anchors | VERDE | `beacon/services/audit_chain.py` (compute_chain_hash + anchor_to_citadel) wired em hot path |
| 12 | PULSE observability | VERDE | structlog JSON + Prometheus `/metrics`; canonical labels per-provider em routers |
| 13 | Tests >70% cov | VERDE | 45/45 tests pass — 83% cov em `messaging_cp.*` (Python 3.11) |
| 14 | OpenAPI 3.1 | VERDE | FastAPI auto-gen em `/openapi.json`; dump script `scripts/dump_openapi.py` |
| 15 | SDK clients Py+TS | VERDE | `sdk/python/messaging/__init__.py` + `sdk/typescript/src/index.ts` |
| 16 | Authentik OIDC | VERDE | `architecture/identity/authentik-blueprints/10-providers/provider-rewire-messaging.yaml` |
| 17 | Vault paths | VERDE | `values.yaml` externalSecrets + LGPD.md §5 + README |
| 18 | README | VERDE | `services/rewire-messaging/README.md` |
| 19 | smoke.sh | VERDE | `tests/smoke.sh` — 7 sections, 13 assertions |
| 20 | Frontend MSW mocks | VERDE | `apps/beacon-ui/src/mocks/{handlers,browser}.ts` (todos canonical /v1 endpoints) |

### Correções pós-V0 done

| CORR | Data | Impacto messaging |
|---|---|---|
| CORR-1 | 2026-05-26 | AUDIT `product_registry.py` port `:8000` → `:8080` (alinhamento Helm canonical) |
| CORR-2 | 2026-05-26 | (a) `push.py` web platform: `NotImplementedError` → `410 Gone` + `Sunset` header; (b) `beacon/agents/agent_invoke_router.py`: 501 → 404 capability_not_found; (c) RED middleware **adicionado** (`beacon/red_middleware.py` + wired em `beacon/main.py`) |
| CORR-3 | 2026-05-26 | `service.port` Helm: 80 → **8080** (canônico — alinha Dockerfile EXPOSE 8080 + AUDIT product_registry base_url) |

---

## 3. Arquitetura

```
                                                  emitters
                  ┌────────────────────────────────────────────────────────────┐
                  │  TODOS produtos Rewire (app/admin/deploy/sentinel/audit/   │
                  │  finops/foundry/security/pulse/...) + apps cliente externos │
                  └────────────────────────┬───────────────────────────────────┘
                                           │  REST POST /v1/{emails,sms,push}
                                           │  Bearer OIDC ou bcn_live_… API key
                                           │  X-Organization-Id (RLS scope)
                                           v
       ┌──────────────────────────────────────────────────────────────────────┐
       │ Kong ingress (rate-limit-1k + correlation-id + oidc-authentik plugin) │
       │ host: messaging.rewirelabs.dev  (alias: beacon.rewirelabs.dev /90d)   │
       └──────────────────────────────────┬───────────────────────────────────┘
                                          v
       ┌──────────────────────────────────────────────────────────────────────┐
       │ rewire-messaging control-plane (FastAPI 0.115 / Python 3.13)         │
       │   /healthz /ready /metrics                                            │
       │   /v1/emails     [canonical messaging_cp.api.v1.emails]               │
       │   /v1/sms        [canonical messaging_cp.api.v1.sms]                  │
       │   /v1/push       [canonical messaging_cp.api.v1.push]   (web→410)    │
       │   /v1/templates  [canonical messaging_cp.api.v1.templates]           │
       │   /v1/webhooks/{postal|resend|zenvia|apns|fcm}  [inbound provider]   │
       │   /v1/notifications  [legacy umbrella dispatcher /90d sunset]        │
       │   /v1/lgpd/{dsar,export,delete,correct}  [legacy beacon.api.lgpd]    │
       │   RED middleware (CORR-2 NEW)  • TenancyMiddleware (RLS scope set)   │
       └─────┬───────────┬──────────────┬──────────────┬──────────────────────┘
             │           │              │              │
             v           v              v              v
   ┌────────────────┐ ┌─────────┐ ┌───────────┐ ┌────────────────────┐
   │ Email router   │ │ SMS rtr │ │ Push rtr  │ │ Webhook normalizer │
   │ • Postal (1°)  │ │ Zenvia  │ │ APNs+FCM  │ │ HMAC verify        │
   │ • Resend (2°)  │ │ (CB)    │ │ (CB each) │ │ pgmq event ingest  │
   │ • CB 3-fail/30s│ │         │ │ web→410   │ │                    │
   └────────┬───────┘ └────┬────┘ └─────┬─────┘ └─────────┬──────────┘
            │              │            │                 │
            └──────────────┴────────────┴─────────────────┘
                                         │
                                         v
        ┌───────────────────────────────────────────────────────────────────┐
        │ pgmq queues (Postgres 17 extension)                               │
        │  • msg_outbound (sender_worker drains → adapter routers)          │
        │  • msg_retry    (retry_worker exponential backoff + DLQ)          │
        │  • msg_dlq      (30d retention; manual replay)                    │
        │  Migration: apps/control-plane/migrations/versions/0005_pgmq_queues.py │
        └──────────────────────────────┬────────────────────────────────────┘
                                       │
                                       v
        ┌───────────────────────────────────────────────────────────────────┐
        │ Postgres CNPG 17 (schema messaging)  • RLS FORCE on all tables    │
        │ Redis 7.4 (quota/rate)                                            │
        │ Vault/OpenBao (secret/data/rewire/messaging/*)                    │
        │ Kafka Strimzi + RabbitMQ 4.x (legacy beacon retry/DLQ /90d)       │
        │ Temporal 1.25 (multi-channel journeys — backlog V0.4)             │
        │ ClickHouse 24.x (analytics ingest — backlog V0.4)                 │
        │ Authentik OIDC (issuer auth.rewirelabs.dev/application/o/messaging/)│
        └───────────────────────────────────────────────────────────────────┘
                                       │
                                       v
        ┌───────────────────────────────────────────────────────────────────┐
        │ Cross-product anchors per dispatch (synchronous fire-and-forget): │
        │  • CITADEL chain hash BLAKE3 → POST /citadel/v1/anchor            │
        │  • AUDIT compliance evidence → POST /audit/v1/evidence            │
        │  • Lago metric emit (billable count) → POST /lago/billable_metrics │
        │  • Credits emit (wallet decrement if weight>0) → wallet-api       │
        └───────────────────────────────────────────────────────────────────┘
```

### Components — código canonical

| Component | Path | Função |
|---|---|---|
| Canonical namespace | `apps/control-plane/src/messaging_cp/__init__.py` | Re-exports + co-mount glue |
| Email adapters | `messaging_cp/adapters/email/{postal,resend,router}.py` | Postal primário + Resend fallback + CB |
| SMS adapter | `messaging_cp/adapters/sms/{zenvia,router}.py` | Zenvia BR (E.164 validation) |
| Push adapters | `messaging_cp/adapters/push/{apns,fcm,router}.py` | APNs HTTP/2 + FCM v1; web→410 |
| pgmq queues | `messaging_cp/queues/{sender_worker,retry_worker}.py` | Async dispatch + retry |
| Credits emit | `messaging_cp/credits_emit.py` | Weights 0/2/0; fail-soft |
| Lago emit | `messaging_cp/lago_emit.py` | `emit_messaging_billable()` |
| RED middleware | `apps/control-plane/src/beacon/red_middleware.py` (CORR-2 NEW) | http_requests_total + duration histogram |
| Audit chain | `beacon/services/audit_chain.py` | BLAKE3 hash + CITADEL anchor |
| Resend fallback client | `beacon/integrations/resend.py` | httpx client + retry policy |

### Resend fallback — quando aciona

O `messaging_cp.adapters.email.router` aplica circuit breaker **per-provider** com window 3-fail-30s:

1. Tentativa Postal (primário, self-hosted).
2. Em **5xx ou CB-open**, tenta Resend (US, fallback).
3. Em **ambos falham**, retorna `502 email_all_providers_failed` (RFC 7807).
4. Webhook de delivery confirma status async (`POST /v1/webhooks/{postal|resend}`).

LGPD: Resend acionamento documentado em `LGPD.md §6` — transfer Art. 33-IX (execução de contrato), tenant DPA deve disclosure.

### pgmq vs Kafka

V0 usa **pgmq** (Postgres extension) para `msg_outbound` / `msg_retry` / `msg_dlq` — simpler ops, transactional dedup nativo. Kafka Strimzi permanece para fan-out volumoso analytics (legacy beacon path, backlog V0.4 consolidação total para pgmq).

---

## 4. Decisões canonical (ADRs)

### ADRs locais (`services/rewire-messaging/docs/adr/`)

| ADR | Decisão | Status |
|---|---|---|
| 0001 | Backend language: FastAPI 0.115 + Python 3.13 (alinhado cluster-wide) | Accepted |
| 0002 | Data model: Postgres CNPG 17 (transacional) + ClickHouse 24.x (analytics, V0.4) | Accepted |
| 0003 | Auth: Authentik OIDC + per-tenant API tokens (`bcn_live_…`) | Accepted |
| 0004 | Multi-tenancy: RLS FORCE Postgres (`organization_id` + policy `org_isolation`) | Accepted |
| 0005 | Cross-product integrations: REST internal (no shared DB) | Accepted |
| 0006 | Compat: namespace canonical universal notification surface (legacy compat via /v1/notifications dispatcher) | Accepted |

### ADRs cluster-wide relevantes

| ADR | Decisão | Aplicação messaging |
|---|---|---|
| **ADR 0108 §C2** | Umbrella consolidation `rewire-notify` + `rewire-beacon` → `rewire-messaging` | Define umbrella scope + 90d legacy redirect `beacon.rewirelabs.dev` |
| **ADR 0042** | Webhook standards + audit chain por evento | HMAC sig verification em `/v1/webhooks/{provider}` + CITADEL anchor |

### Decisões binárias V0

- **Postal self-hosted ANTES de SES** — soberania BR + reputation management próprio. SES é roadmap V0.4 high-volume burst.
- **Resend fallback US** — porque Postal solo sem fallback = SPOF. Resend tem DPA Art. 33-IX justificável.
- **Zenvia primário ANTES de TotalVoice** — parceria revenue-share 15-25% firmada; TotalVoice fallback V0.1 backlog.
- **APNs/FCM direto** — sem intermediário (Apple/Google grátis); intermediários (OneSignal/Braze) custam margem.
- **Web Push 410 Gone V0** — VAPID + Service Worker complexity excede V0 budget; ships V0.3 (não bloqueia mobile push).
- **pgmq sobre Kafka V0** — simpler ops; Kafka mantido legacy beacon paths /90d.
- **RLS FORCE Postgres** (não app-layer filtering) — isolação defesa-em-profundidade; `beacon_worker` role tem `BYPASSRLS` somente para fan-out cross-tenant DLQ.

---

## 5. APIs detalhadas

Spec autoritativa: `docs/products/messaging/API_CONTRACT.md` (v0.2.0). Resumo abaixo — sempre validar contra OpenAPI gerado (`/openapi.json`).

### Auth

- `Authorization: Bearer <oidc_jwt>` (Authentik, scope per `messaging:*`)
- OR `Authorization: Bearer bcn_live_<tenant_token>` (per-tenant API key)
- `X-Organization-Id: org_<uuid>` (cross-org keys; obrigatório p/ RLS scope)

### Scopes OIDC

| Scope | Permissão |
|---|---|
| `messaging:send` | Send any channel (emails/sms/push) |
| `messaging:read` | Read status, templates |
| `messaging:admin` | Templates CRUD, webhook config |
| `messaging:dsar` | LGPD export/delete |

### Endpoints canonical /v1

#### Email

**`POST /v1/emails`** → 202 (queued via pgmq → Postal/Resend)

```jsonc
// Request
{
  "sender": "noreply@tenant.com",
  "to": ["alice@example.com"],
  "subject": "Bem-vinda!",
  "html_body": "<p>Olá Alice</p>",
  "plain_body": "Ola Alice",
  "reply_to": "support@tenant.com",
  "template_id": "tpl_welcome",
  "tag": "transactional",
  "consent_basis": "contract",          // LGPD Art. 7
  "metadata": {"campaign_id": "onboard-v2"}
}
// Response 202
{"message_id": "01HXYZ...", "status": "queued", "provider": "postal"}
```

Errors RFC 7807:
- `422 invalid_recipient` · `422 email_requires_html_or_plain_body`
- `502 email_all_providers_failed` (Postal + Resend ambos failed/CB-open)
- `400 tenant_required`

**`GET /v1/emails/{message_id}`** → 200 `{message_id, status: queued|delivered|bounced}`

#### SMS

**`POST /v1/sms`** → 202 (queued via pgmq → Zenvia)

```jsonc
{
  "to": "+5511999998888",          // E.164 BR validation
  "text": "Seu codigo: 123456",
  "from_number": "Rewire",
  "template_id": "tpl_otp",
  "consent_basis": "consent"
}
// Response 202
{"message_id": "msg_abc...", "status": "queued", "provider": "zenvia", "cost_brl_cents": 7}
```

Errors: `422 invalid_recipient` (não E.164 BR) · `502 sms_all_providers_failed` · `400 tenant_required`

**`GET /v1/sms/{message_id}`** → status

#### Push

**`POST /v1/push`** → 202 (platform decide provider)

```jsonc
{
  "device_token": "abcd1234...",
  "platform": "ios" | "android" | "web",   // web→410 Gone V0.3
  "title": "Você tem um pix de R$ 100",
  "body": "De Alessandro Q.",
  "data": {"deep_link": "rewire://pix/abc"},
  "push_app_id": "app_main"
}
```

Errors: `503 push_circuit_open` (CB open) · `502 push_send_failed` · **`410 push_web_v03`** (web platform, com header `Sunset` apontando V0.3) · CORR-2 fix

**`POST /v1/push/devices`** → 201 (registra device token p/ user_id)

#### Webhooks inbound

**`POST /v1/webhooks/{postal|resend|zenvia|apns|fcm}`** → 204

- Header `X-Webhook-Signature` HMAC per-provider
- 400 `webhook_processing_failed` em bad signature/payload
- Eventos normalizados → pgmq event ingest → CITADEL anchor

#### Templates

| Endpoint | Status |
|---|---|
| `POST /v1/templates` | 201 + body com `{id, slug, channel, locale, version}` |
| `GET /v1/templates/{template_id}` | 200 |
| `GET /v1/templates` | 200 (lista per-tenant) |
| `DELETE /v1/templates/{template_id}` | 204 |

#### Legacy umbrella (90d sunset)

**`POST /v1/notifications`** — dispatcher com `channel` field; delega internamente. Mantido /90d pós-cutover canonical.

### Idempotency

Shape default: `{tenant_id}:{recipient}:{template_id}:{date}` — duplicates dentro do mesmo dia para mesmo template+recipient retornam `message_id` original.

Override explícito: header `Idempotency-Key: <opaque>` desliga date-based dedup.

### Error format (RFC 7807)

```json
{
  "type": "https://errors.rewirelabs.dev/messaging/email_all_providers_failed",
  "title": "Email providers all failed",
  "status": 502,
  "detail": "Postal returned 5xx; Resend CB-open",
  "instance": "/v1/emails",
  "trace_id": "01HXYZ..."
}
```

---

## 6. Data model

### Schema `messaging` (Postgres CNPG 17)

Tabelas core (todas com `organization_id` + RLS FORCE):

| Tabela | Função | Retenção |
|---|---|---|
| `messaging.messages` | Mensagens enviadas (body rendered, status, providers tentados) | **90 dias** (pg_cron purge) |
| `messaging.deliveries` | Eventos webhook (sent/delivered/bounced/opened/clicked) | **90 dias** (pg_cron purge) |
| `messaging.devices` | Device tokens registrados (APNs/FCM) com `pgsodium` em phone/email V0.1 | Até app uninstall ou 365d idle (`bad_token_cleanup.py` weekly) |
| `messaging.suppression` | Opt-outs cross-canal `(tenant_id, identifier, channel)` | **Permanente** (Art. 18-IX) |
| `messaging.templates` | Templates per-tenant (MJML/Handlebars) | Soft delete |
| `messaging.organizations` | Cache tenant metadata + plan tier | n/a |
| `messaging.message_metadata` | Hashes BLAKE3 + anchors CITADEL | **5 anos** (Art. 37) |
| `messaging.dlq_events` | DLQ pgmq replay queue | **30 dias** |

### RLS FORCE policy

```sql
-- Aplicada em TODAS as tabelas business:
ALTER TABLE messaging.<table> ENABLE ROW LEVEL SECURITY;
ALTER TABLE messaging.<table> FORCE ROW LEVEL SECURITY;

CREATE POLICY org_isolation ON messaging.<table>
  USING (organization_id = current_setting('beacon.current_org_id', true)::uuid);

-- Worker role (BYPASSRLS) para fan-out + DLQ cross-tenant:
GRANT BYPASSRLS TO beacon_worker;
```

`current_setting('beacon.current_org_id')` é populado por `TenancyMiddleware` a partir do JWT/`X-Organization-Id` em cada request.

### pgmq queues

Migration `0005_pgmq_queues.py` cria 3 queues:
- `msg_outbound` — sender_worker drain → adapter routers
- `msg_retry` — retry_worker exponential backoff (max 5 tentativas)
- `msg_dlq` — manual replay (30d retention)

### CITADEL anchor schema

Eventos âncorados:
- `sent` (após provider 202)
- `delivered` (webhook)
- `bounced` (webhook hard/soft)
- `opt_out` (LGPD DSAR / unsubscribe)

Payload BLAKE3:
```
{actor=tenant_id, action, resource=message_id, hash(input+output+metadata), timestamp, tenant_id}
```

---

## 7. Dependencies cross-product

### Emitters (produtos que enviam via messaging)

| Produto | Canais usados | Tipo de notificação |
|---|---|---|
| **rewire-app** | email | Welcome, invoice, payment, password reset |
| **rewire-admin** | email + telegram | Operator notifications, cluster events, impersonation alerts |
| **rewire-deploy** | email + telegram | Deploy success/failure, rollback alerts |
| **rewire-sentinel** | email + slack-mirror | Test failure notifications |
| **rewire-audit** | email | Compliance evidence emission (DSAR ready outputs) |
| **rewire-security** (ex-guardian+phalanx) | email + sms + push | Alert severity=critical multi-canal |
| **rewire-pulse** | email + telegram | Anomaly markers, OTLP delivery failure escalation |
| **rewire-finops** | email | Budget alerts + cost-optimization recommendations |
| **rewire-foundry** | email | Golden path build status, template publish |
| **rewire-citadel** | email | DSAR completion, breach notify |
| **rewire-customer-support** | email + sms | Ticket criação/update/resolve |
| **rewire-servers** (ex-host) | email + push | App provisioning + per-VM status |
| **rewire-ascend** | email | Cross-sell drip emails (transactional opt-in) |
| **rewire-tenant-metering** | email | Plan threshold alerts |
| **rewire-databases** | email | Backup completion, replica lag warnings |

### Provider/dependency (messaging consome)

| Sistema | Como messaging usa |
|---|---|
| **rewire-connect** | WhatsApp dispatch via REST internal `POST /connect/internal/v1/whatsapp/send` (backlog V0.3) |
| **rewire-citadel** | Anchor BLAKE3 hash por mensagem (`POST /citadel/v1/anchor`) |
| **rewire-audit** | Compliance evidence emission (`POST /audit/v1/evidence`) |
| **rewire-tenant-metering** | Plan tier lookup + Lago billable counters |
| **Authentik** | OIDC backbone (issuer `auth.rewirelabs.dev/application/o/messaging/`) |
| **Vault/OpenBao** | Secrets (`secret/data/rewire/messaging/*`) |
| **Postgres CNPG** | Schema `messaging` + pgmq |
| **Redis** | Rate limit + quota cache |
| **PULSE** | OTLP traces + metrics + log shipping |
| **Lago** | Billable metric emission (`messaging_email_sent`/`sms`/`push`/`credits_consumed`) |
| **Asaas** | NF-e downstream (via tenant-metering) |

---

## 8. Pricing tier (Lago metrics)

### Billable metrics declarados (`architecture/lago/billable_metrics_canonical.yaml`)

| Code | Tipo | Field | Use |
|---|---|---|---|
| `messaging_credits_consumed` | Sum (recurring) | `credits` | Wallet impact (carries pricing) |
| `messaging_email_sent` | Count (recurring) | n/a — count delivered | Cost analytics per-channel |
| `messaging_sms_sent` | Count (recurring) | n/a | Cost analytics per-channel |
| `messaging_push_sent` | Count (recurring) | n/a | Cost analytics per-channel |

Group-by metrics: `tenant_id`, `provider`, `channel`, `idempotency_key`.

### Credits weights (canonical)

| Action | Weight | Lago metric |
|---|---|---|
| `email_transactional` | **0** | `messaging_email_sent` |
| `sms_br` | **2** | `messaging_sms_sent` |
| `push_notification` | **0** | `messaging_push_sent` |

V0 economics: **email + push free** (custos provider absorvidos no infra dos planos); **SMS billable BR pass-through** (~R$ 0.10/SMS ao tenant).

### Pricing tier proposta (informativo — Lago é fonte autoritativa)

| Canal | Modelo |
|---|---|
| Email | Tiered Hobby R$ 97 → Scale R$ 2.000+. Postal IPs dedicados Scale+ tier |
| SMS | Markup ~30% sobre Zenvia (~R$ 0,06-0,09 → R$ 0,07-0,12/SMS pass-through) |
| Push iOS/Android | Tiered por volume (grátis APNs/FCM, markup infra/multi-tenant) |
| Push Web | Free V0.3+ (VAPID grátis) |
| WhatsApp (V0.3+) | Pass-through Meta + 30% markup (utility R$ 0,12-0,18 / marketing R$ 0,30-0,50 / auth R$ 0,12-0,15) |
| NF-e | Asaas BR (downstream via tenant-metering) |

Comparação externa: SendGrid USD 19,95/mês mínimo + IOF → MESSAGING R$ 97/mês com NF-e = 40-60% mais barato BR.

---

## 9. Compliance (LGPD — Lei 13.709/2018)

Spec autoritativa: `docs/products/messaging/LGPD.md`. Resumo abaixo.

### Lawful basis matrix (Art. 7)

| Operação | Base legal V0 |
|---|---|
| Transactional email (welcome, OTP, invoice, password reset) | **I — execução de contrato** (Art. 7, V) |
| Transactional SMS (OTP, alerts) | **I — execução de contrato** |
| Push notification transactional | **I — execução de contrato** (OS-level opt-in) |
| Marketing email broadcast | **V — consentimento** OR **XII — legítimo interesse** (tenant doc obrigatória) |
| Cross-channel suppression | **III — obrigação legal** (Art. 18 oposição) |
| CITADEL audit chain anchor | **III — obrigação legal** (Art. 37 records 5 anos) |
| Webhook re-delivery + DLQ | **I — execução de contrato** (bounded 30d) |
| Lago billing emit | **III — obrigação legal** (NF-e fiscal) |

### DSAR endpoints (Art. 18)

| Direito | Endpoint | Implementação |
|---|---|---|
| I — confirmação existência | `GET /v1/lgpd/dsar?recipient=...` | `beacon.api.lgpd` V0 |
| II — acesso/export | `GET /v1/lgpd/export?recipient=...` | JSON dump PII + delivery history |
| III — correção | `PATCH /v1/lgpd/correct` | V0.1 backlog |
| IV — anonimização/eliminação | `DELETE /v1/lgpd/delete?recipient=...` | Hard delete messages/deliveries/devices/suppression; CITADEL preserva só hash anchor |
| V — portabilidade | Same as II | JSON-LD portable shape |
| VIII — revogação consentimento | `POST /v1/suppression` + unsub link | Cross-channel suppression |

**SLA DSAR: 15 dias** (ANPD recommendation 2025). Audit chain registra toda ação DSAR.

### Retention policies

| Categoria | Retenção | Justificativa |
|---|---|---|
| Message body (rendered) | **90 dias** | Debug + customer support window (pg_cron purge) |
| Message metadata (status, hashes) | **5 anos** | Art. 37 record-keeping + fiscal NF-e |
| Provider webhook events | **90 dias** | Debug + reconciliation |
| Device tokens (push) | App uninstall ou **365d idle** | `bad_token_cleanup.py` worker weekly |
| Suppression list | **Permanente** | Art. 18-IX (oposição) |
| CITADEL chain entries | **10 anos** | Forensic + obrigação legal |
| Audit logs (admin/impersonation) | **5 anos** | Art. 37 |

### International transfers (Art. 33)

- **Resend** (fallback email) — US-hosted; Art. 33-IX execução de contrato; DPA `resend.com/legal/dpa`.
- **APNs (Apple)** — US-hosted; necessário p/ push iOS; Art. 33-IX.
- **FCM (Google)** — US-hosted; necessário p/ push Android; Art. 33-IX.
- **Zenvia** — BR-only, **sem transfer**.
- **Postal** — self-hosted BR (Magalu Cloud sa-east-1 ou Proxmox cluster), **sem transfer**.

Tenant DPA deve disclosure sub-processors. ANPD adequacy US pending (2024+); meanwhile contractual safeguards + tenant DPA consent.

### Breach notification (Art. 48)

48h SLA detect → ANPD + data subjects.

Process:
1. Detect via PULSE alert (spam anomaly, mass bounce, exfiltration pattern).
2. Trigger workflow `messaging.breach.notify` (Temporal V0.5+; V0 manual via cluster-team Telegram).
3. ANPD form pre-filled (`POST /v1/audit/lgpd/breach-notify`).
4. Email affected subjects via Postal high-priority queue.
5. Anchor breach event CITADEL chain.

### Special categories (Art. 11)

**NÃO aceitos**: credenciais, dados de saúde, biométricos. Tenant deve filtrar upstream.

---

## 10. Observability

### Metrics (Prometheus `/metrics`)

Endpoint `/metrics` (port 8080) scraped pelo ServiceMonitor (`prometheus.serviceMonitor.enabled: true`, interval 30s).

Canonical labels per métrica:
- `tenant_id`
- `product=messaging`
- `channel=email|sms|push`
- `provider=postal|resend|zenvia|apns|fcm`
- `status=queued|sent|delivered|bounced|failed`

RED middleware (CORR-2 NEW — `beacon/red_middleware.py`):
- `http_requests_total{method, route, status_code, product}` — counter
- `http_request_duration_seconds{method, route, product}` — histogram

Domain metrics:
- `messaging_dispatch_total{channel, provider, outcome}` — counter
- `messaging_webhook_events_total{provider, event_type}` — counter
- `messaging_circuit_breaker_state{provider}` — gauge (0=closed, 1=open, 2=half-open)
- `messaging_pgmq_queue_depth{queue_name}` — gauge

### PrometheusRule alerts (canonical CORR-D2)

Localização: `architecture/products/messaging/helm/templates/prometheusrule.yaml`.

- `MessagingHighErrorRate` — 5xx >5% por 5min
- `MessagingHighLatency` — p99 >2s por 10min
- `MessagingBurnRate` — multi-window SLO burn 99.9%
- `MessagingProviderCBOpen` — circuit breaker open >5min
- `MessagingDLQGrowing` — DLQ depth >100 mensagens
- `MessagingSaturation` — CPU >80% por 15min (HPA target 70%)

### Tracing (OTLP)

Headers propagated: `traceparent`, `tracestate`, `x-request-id`.
Exporter: `MESSAGING_OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.observability.svc.cluster.local:4317`.
Spans: ingress → router → adapter → provider call → webhook callback.

### Logs

structlog JSON com **sempre** `tenant_id`, `trace_id`, `request_id`. PII redacted via redactor middleware (emails/phones hashed).

### Dashboards

- Grafana folder `messaging/` — pre-existing dashboards beacon legacy + canonical em V0.4 (referência PULSE).

---

## 11. Security

### Authentik OIDC

- Blueprint canonical: `architecture/identity/authentik-blueprints/10-providers/provider-rewire-messaging.yaml`
- Client ID: `messaging` (env `MESSAGING_OIDC_CLIENT_ID`)
- Issuer: `https://auth.rewirelabs.dev/application/o/messaging/`
- Client secret: Vault `kv/rewire-messaging/oidc#client_secret`
- Scopes: `messaging:send`, `messaging:read`, `messaging:admin`, `messaging:dsar`
- Kong plugin `oidc-authentik` enforced em ingress
- Per-tenant API keys (`bcn_live_…`) bypass OIDC mas têm escopo limitado a `X-Organization-Id`

### Vault paths (canonical pos-ADR 0108 §C2)

Backend: ESO `ClusterSecretStore name=vault-kv`, refresh 30min.

| Path Vault | Secret materializado em K8s |
|---|---|
| `kv/rewire-messaging/database#url` | `MESSAGING_DATABASE_URL` |
| `kv/rewire-messaging/redis#url` | `MESSAGING_REDIS_URL` |
| `kv/rewire-messaging/rabbitmq#url` | `MESSAGING_RABBITMQ_URL` (legacy beacon path /90d) |
| `kv/rewire-messaging/oidc#client_secret` | `MESSAGING_OIDC_CLIENT_SECRET` |
| `kv/rewire-messaging/postal#api_key` | `MESSAGING_POSTAL_API_KEY` |
| `kv/rewire-messaging/resend-api-key#value` | `MESSAGING_RESEND_API_KEY` |
| `kv/rewire-messaging/zenvia#api_token` | `MESSAGING_ZENVIA_API_TOKEN` |
| `kv/rewire-messaging/telegram-bot-token#value` | `MESSAGING_TELEGRAM_BOT_TOKEN` (legacy notify migrated) |
| `kv/rewire-messaging/telegram-chat-id-private#value` | `MESSAGING_TELEGRAM_CHAT_ID_PRIVATE` |
| `kv/rewire-messaging/telegram-chat-id-group#value` | `MESSAGING_TELEGRAM_CHAT_ID_GROUP` |

Per-tenant scoped paths (formato canonical):
- `secret/data/rewire/messaging/{tenant}/postal/{domain}/dkim`
- `secret/data/rewire/messaging/{tenant}/ses/credentials` (V0.4 SES adoption)
- `secret/data/rewire/messaging/{tenant}/zenvia/api-token`
- `secret/data/rewire/messaging/{tenant}/apns/{bundle_id}/cert` (`.p8` Apple Developer account)
- `secret/data/rewire/messaging/{tenant}/fcm/{project_id}/key` (service account JSON)
- `secret/data/rewire/messaging/{tenant}/vapid/{origin}/keypair` (V0.3 web push)

Procedimento migration legacy paths ex-notify/ex-beacon: `docs/runbooks/vault-path-migration-messaging.md`.

### NetworkPolicy

`architecture/products/messaging/helm/templates/networkpolicy.yaml` — ingress permitido somente de namespaces `kong` (HTTP traffic) + `observability` (scrape `/metrics`).

### Pod security

- `runAsNonRoot: true` · `runAsUser: 65532` · `fsGroup: 65532`
- `readOnlyRootFilesystem: true` (volume `tmp` emptyDir mounted em `/tmp`)
- `allowPrivilegeEscalation: false` · `capabilities.drop: [ALL]`
- `seccompProfile.type: RuntimeDefault`

### TLS

- Ingress Kong + cert-manager (issuer `letsencrypt-prod-cloudflare`)
- Secret TLS: `wildcard-rewire-cluster-tls`
- Cluster-internal: mTLS via Cilium

### PII encryption

- At rest: Postgres CNPG TDE (LUKS-encrypted Ceph OSDs) + `pgsodium` column-level p/ `phone`/`email` em `messaging.devices` (V0.1)
- In transit: TLS 1.3 + HSTS public; mTLS Cilium cluster-internal
- Logs: redactor middleware hashes emails/phones antes de structlog emit

### Webhook signature verification

Cada `/v1/webhooks/{provider}` valida HMAC per-provider:
- Postal: `X-Postal-Signature` (sha256)
- Resend: `X-Resend-Signature` (sha256 HMAC)
- Zenvia: `X-Zenvia-Signature` (HMAC sha256)
- APNs: token-based (HTTP/2 connection auth)
- FCM: signed-JWT verify

---

## 12. Roadmap

| Versão | Escopo | ETA |
|---|---|---|
| **V0.1** (unblock) | Build + push imagem `dev-latest` registry + redeploy + deployment volta online | Pós-FASE E (este lote) |
| **V0.2** | (a) Postal MTA pool warm-up 30d novos IPs + AWS SES fallback wire; (b) Zenvia/TotalVoice clients full + cost-aware routing; (c) APNs/FCM production load; (d) Template MJML render service | Q3 2026 |
| **V0.3** | (a) WhatsApp via rewire-connect internal API; (b) VAPID Web Push (RFC 8030); (c) DSAR `PATCH /v1/lgpd/correct` + suppression bulk import | Q4 2026 |
| **V0.4** | (a) ClickHouse 24.x analytics (bilhões msgs); (b) Temporal worker journeys multi-step ("se não abrir email 24h → SMS → WA 48h"); (c) Anti-spam ML preventivo (scikit-learn + sentence-transformers); (d) Kafka consolidation → pgmq full | Q1 2027 |
| **V0.5** | (a) A/B testing nativo; (b) UI Lovable 19 telas herdadas beacon (rework UX simplification); (c) Billing Lago wire + NF-e Asaas downstream | Q2 2027 |
| **V0.6** | DSAR full + suppression list cross-canal unified BR/world | Q3 2027 |
| **V1** | (a) Stalwart Mail Server alternativa Postal; (b) Voice calling (BSP parceria); (c) Audit chain ICP-Brasil sign + LTO-9 cold archive | 2028 |
| **V2** | Multi-region active-active + DR drill quarterly | 2028+ |

**ARR target ano 3 (2028)**: R$ 8M

### Open operator follow-up (out-of-scope agent)

1. Install Postal sub-chart + DNS `postal.messaging.svc.cluster.local`.
2. Populate Vault paths: `secret/data/rewire/messaging/{postal_api_key, resend_api_key, zenvia_token, apns_keys, fcm_service_account}`.
3. Provision APNs `.p8` (Apple Developer account) + FCM service account JSON (Firebase project).
4. Apply migration `0005_pgmq_queues.py` quando pgmq extension enabled cluster-wide em CNPG.
5. Build + push image `192.168.1.110:30500/rewire-labs/rewire-messaging-control-plane:dev-latest` (P0 sistêmico atual bloqueando deployment ~10h).
6. Validar Authentik OIDC blueprint sync pós-deploy.

---

## Referências

- Spec V0 done: `tickets/_status/AGENT_MESSAGING_PROGRESS.md`
- API contract autoritativo: `docs/products/messaging/API_CONTRACT.md`
- LGPD compliance matrix: `docs/products/messaging/LGPD.md`
- Helm canonical: `architecture/products/messaging/helm/`
- ADRs locais: `services/rewire-messaging/docs/adr/` (0001-0006)
- ADR 0108 §C2 (umbrella): `docs/adr/0108-*.md`
- ADR 0042 (webhook standards): `docs/adr/0042-*.md`
- CORR-1 (port + AppSet + OIDC + Lago sweeps): `audits/CORR_1_CROSS_SLOT_REPORT.md`
- CORR-2 (501 + RED middleware): `audits/CORR_2_DEAD_CODE_AND_501_REPORT.md`
- CORR-3 (service port 8080): `audits/CORR_3_HELM_CANONICAL_REPORT.md`
- Spec legacy preservada: `services/rewire-messaging/BEACON.md` (1008 linhas — push/SMS V0 decisions)
- MESSAGING product summary: `services/rewire-messaging/MESSAGING.md`
- README developer-facing: `services/rewire-messaging/README.md`
- Authentik blueprint: `architecture/identity/authentik-blueprints/10-providers/provider-rewire-messaging.yaml`
- Lago metrics: `architecture/lago/billable_metrics_canonical.yaml` (lines 168-215)

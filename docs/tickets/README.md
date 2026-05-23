# Tickets — rewire-beacon

Backlog organizado por phase. Status `[ ]` / `[x]`. Cross-reference via
`[[ID]]`.

> **Contexto**: BEACON está em **V0 skeleton** apenas. Implementado:
> - `apps/control-plane/` FastAPI com `/healthz`, `/ready`, `/metrics` +
>   4 stub routers (notifications, templates, deliveries, webhooks)
>   retornando `{"status":"not_implemented","todo":"V0.2"}`
> - Migration 0001 cria 5 tabelas básicas (`tenants`, `channels`,
>   `templates`, `notifications`, `deliveries`)
> - UI `apps/beacon-ui/` com 19 pages Lovable + mocks completos
> - 5 ADRs criadas (audit 2026-05-23)
>
> Gaps massivos: zero workers, zero providers wired (Postal/AWS SES/
> Zenvia/APNs/FCM/VAPID), zero Kafka producers/consumers, zero
> Temporal workflows, zero ClickHouse, zero anti-spam ML, zero
> billing wire, zero auth real.

## Phase 0 — Bootstrap (concluído)

| ID | Título | Status |
|---|---|---|
| [[BCN-001]] | Bootstrap workspace Python 3.13 + FastAPI | [x] |
| [[BCN-002]] | Migration 0001 schema básico (5 tabelas) | [x] |
| [[BCN-003]] | UI Lovable 19 pages com mocks | [x] |
| [[BCN-004]] | docs/api/API_SPEC.md spec endpoints | [x] |
| [[BCN-005]] | 5 ADRs cobrindo decisões estruturais | [x] |

## Phase 1 — Foundation (V0.1 — schema + auth + multi-tenancy)

Construir foundation production-ready para suportar fluxos reais.

| ID | Título | Status | Owner |
|---|---|---|---|
| [[BCN-010]] | Migration 0002 expandir schema para 10+ tabelas (senders, suppression, webhooks, providers) ver [[ADR-0002]] | [x] | backend |
| [[BCN-011]] | Migration 0003 RLS FORCE + POLICY org_isolation em todas as tabelas multi-tenant ver [[ADR-0004]] | [x] | backend |
| [[BCN-012]] | Migration 0004 role `beacon_worker` com BYPASSRLS | [x] | backend |
| [[BCN-013]] | Middleware auth.py JWT Authentik (UI) + API token (SDK) ver [[ADR-0003]] | [x] | backend |
| [[BCN-014]] | Middleware tenancy.py SET GUC `beacon.current_org_id` | [x] | backend |
| [[BCN-015]] | Middleware idempotency.py (Redis SHA256 24h TTL) | [x] | backend |
| [[BCN-016]] | Service `services/api_tokens.py` (criação + bcrypt + revogação) | [x] | backend |
| [[BCN-017]] | Endpoint `POST/GET/DELETE /v1/api-tokens` ver [[ADR-0003]] | [x] | backend |
| [[BCN-018]] | Tests RLS isolation cross-tenant em 10+ tabelas | [x] | qa |

## Phase 2 — Email channel (V0.1 — Postal primary + AWS SES fallback)

Primeiro canal a entregar para clientes beta.

| ID | Título | Status | Owner |
|---|---|---|---|
| [[BCN-020]] | Postal infrastructure: helm chart 8 nodes + IP pool 60 IPs BR | [ ] | infra |
| [[BCN-021]] | Cliente HTTP `integrations/postal.py` (send + bounce/complaint) | [x] | backend |
| [[BCN-022]] | Cliente HTTP `integrations/aws_ses_br.py` (fallback Scale+) | [x] | backend |
| [[BCN-023]] | Worker Kafka consumer `workers/email_sender.py` | [x] | backend |
| [[BCN-024]] | Endpoint `POST /v1/messages/email` body real (substituir stub) ver [[ADR-0002]] | [x] | backend |
| [[BCN-025]] | Email domain verification flow (DKIM/SPF/DMARC) | [x] | backend |
| [[BCN-026]] | Endpoint `POST /v1/domains` + `POST /v1/domains/{id}/verify` | [x] | backend |
| [[BCN-027]] | Postal vhost provisioning per org ver [[ADR-0004]] | [x] | backend+infra |
| [[BCN-028]] | Email template rendering MJML + Handlebars-like vars | [x] | backend |
| [[BCN-029]] | Tests E2E: criar org → adicionar domain → verify DNS → enviar email → callback bounce | [ ] | qa |

## Phase 3 — Suppression list + bounce/complaint handling (V0.1)

| ID | Título | Status | Owner |
|---|---|---|---|
| [[BCN-035]] | Service `services/suppression.py` (add/remove/check) | [x] | backend |
| [[BCN-036]] | Cross-canal suppression check ANTES de cada envio (latência <2ms) | [x] | backend |
| [[BCN-037]] | Endpoint `POST/GET/DELETE /v1/suppression` | [x] | backend |
| [[BCN-038]] | Portal público `/u/{unsubscribe_token}` (LGPD Art. 18) | [x] | backend+frontend |
| [[BCN-039]] | Postal webhook handler `bounce`/`complaint` → auto-add suppression | [x] | backend |
| [[BCN-040]] | Tests bounce/complaint handling end-to-end | [x] | qa |

## Phase 4 — SMS channel (V0.2)

| ID | Título | Status | Owner |
|---|---|---|---|
| [[BCN-050]] | Cliente HTTP `integrations/zenvia.py` (primary BR) | [x] | backend |
| [[BCN-051]] | Cliente HTTP `integrations/totalvoice.py` (fallback BR) | [x] | backend |
| [[BCN-052]] | Worker Kafka consumer `workers/sms_sender.py` com BSP routing | [x] | backend |
| [[BCN-053]] | Endpoint `POST /v1/messages/sms` body real | [x] | backend |
| [[BCN-054]] | Two-way SMS receiver webhook (BSP → BEACON) | [x] | backend |
| [[BCN-055]] | Pricing pass-through + markup transparente (BEACON.md §2.2.2) | [x] | backend |
| [[BCN-056]] | Acordo comercial Zenvia/TotalVoice (revenue share) | [ ] | comercial |

## Phase 5 — Push mobile (V0.2)

| ID | Título | Status | Owner |
|---|---|---|---|
| [[BCN-060]] | Cliente APNs `integrations/apns.py` (aioapns lib) | [x] | backend |
| [[BCN-061]] | Cliente FCM `integrations/fcm.py` (Google Cloud Python lib) | [x] | backend |
| [[BCN-062]] | Worker `workers/push_sender.py` (mobile fan-out) | [x] | backend |
| [[BCN-063]] | Endpoint `POST /v1/messages/push` body real | [x] | backend |
| [[BCN-064]] | Cert/key upload management (APNs .p8, FCM service-account JSON) | [x] | backend |
| [[BCN-065]] | Bad device token cleanup background job | [x] | backend |
| [[BCN-066]] | SDK iOS (Swift) + Android (Kotlin) — separate repos cluster ADR 0043 | [ ] | backend |

## Phase 6 — Push web (V0.3)

| ID | Título | Status | Owner |
|---|---|---|---|
| [[BCN-070]] | Cliente `integrations/webpush.py` (pywebpush lib) | [x] | backend |
| [[BCN-071]] | VAPID key management per org | [x] | backend |
| [[BCN-072]] | Service Worker JS snippet generator | [x] | frontend |
| [[BCN-073]] | Endpoint `POST /v1/messages/push` web channel | [x] | backend |
| [[BCN-074]] | Subscription management endpoints | [x] | backend |

## Phase 7 — WhatsApp (depende CONNECT GA Q3 2026)

| ID | Título | Status | Owner |
|---|---|---|---|
| [[BCN-080]] | Cliente HTTP `integrations/connect.py` ver [[ADR-0005]] | [ ] | backend |
| [[BCN-081]] | Worker `workers/whatsapp_sender.py` delega CONNECT | [ ] | backend |
| [[BCN-082]] | Endpoint `POST /v1/messages/whatsapp` body real | [ ] | backend |
| [[BCN-083]] | Template sync background: CONNECT (approved Meta) → BEACON | [ ] | backend |
| [[BCN-084]] | Quality rating display em UI BeaconWhatsapp.tsx | [ ] | frontend |

## Phase 8 — Analytics ClickHouse (V0.2+)

| ID | Título | Status | Owner |
|---|---|---|---|
| [[BCN-090]] | ClickHouse cluster provisioning Helm chart 3 nodes | [ ] | infra |
| [[BCN-091]] | ClickHouse database `beacon_events` + tabelas + MV ver [[ADR-0002]] | [ ] | backend |
| [[BCN-092]] | Kafka topics `beacon.events.<channel>` via Strimzi CRDs | [ ] | infra |
| [[BCN-093]] | ClickHouse Kafka engine table consumindo tópicos | [ ] | backend |
| [[BCN-094]] | Endpoint `GET /v1/analytics/messages` query ClickHouse + cache Redis 5min | [ ] | backend |
| [[BCN-095]] | Endpoint `GET /v1/messages/{id}/events` timeline | [ ] | backend |
| [[BCN-096]] | Daily stats materialized view refresh | [ ] | backend |

## Phase 9 — Workflows Temporal (V0.3 — multi-channel journeys)

| ID | Título | Status | Owner |
|---|---|---|---|
| [[BCN-100]] | Temporal cluster setup compartilhado cluster Rewire | [ ] | infra |
| [[BCN-101]] | Workflow `MultiChannelJourneyWorkflow` (BEACON.md §2.9) | [ ] | backend |
| [[BCN-102]] | Activities: `send_message_<channel>`, `check_suppression`, etc | [ ] | backend |
| [[BCN-103]] | Endpoint `POST /v1/journeys` + `/start` + `/pause` + `/resume` | [ ] | backend |
| [[BCN-104]] | Visual flow builder UI BeaconJourneys.tsx (similar n8n) | [ ] | frontend |
| [[BCN-105]] | Quiet hours respect timezone do recipient | [ ] | backend |
| [[BCN-106]] | Frequency capping cross-canal | [ ] | backend |

## Phase 10 — Anti-spam ML (V0.4+)

| ID | Título | Status | Owner |
|---|---|---|---|
| [[BCN-110]] | Service Python anti-spam ML (scikit-learn + sentence-transformers) | [ ] | backend |
| [[BCN-111]] | Pattern detection: bulk new sender + suspect content | [ ] | backend |
| [[BCN-112]] | Pre-send check integrated em hot path (latência <50ms) | [ ] | backend |
| [[BCN-113]] | Customer success alert quando bloqueio preventivo | [ ] | backend |
| [[BCN-114]] | Whitelist managed para falsos positivos | [ ] | backend |
| [[BCN-115]] | Training data labeled (BEACON.md §2.13 CapEx Enterprise) | [ ] | data |

## Phase 11 — LGPD + Audit Chain (V0.2)

| ID | Título | Status | Owner |
|---|---|---|---|
| [[BCN-120]] | BLAKE3 hash per message (content + recipient + timestamp + consent_basis) ver [[ADR-0005]] | [ ] | backend |
| [[BCN-121]] | CITADEL chain anchor: POST `/chain/append` per message | [ ] | backend |
| [[BCN-122]] | Endpoint `POST /v1/audit/lgpd/dsar` (Art. 18 export) | [ ] | backend |
| [[BCN-123]] | Lawful basis tag obrigatório em send (consent/contract/legal/legitimate) | [ ] | backend |
| [[BCN-124]] | Breach notification automático 3-day (LGPD ANPD) | [ ] | backend |
| [[BCN-125]] | Cross-canal unsubscribe centralizado portal `/u/<token>` | [ ] | backend+frontend |

## Phase 12 — Billing wire (V0.2)

| ID | Título | Status | Owner |
|---|---|---|---|
| [[BCN-130]] | Cliente HTTP `integrations/lago.py` | [ ] | backend |
| [[BCN-131]] | Lago billable_metrics: emails_count, sms_count, push_count, wa_count, dedicated_ip_count | [ ] | backend |
| [[BCN-132]] | Worker `tasks/usage_reporter.py` (5min cron) reporta consumo | [ ] | backend |
| [[BCN-133]] | NFe.io integration para faturamento BR | [ ] | backend |
| [[BCN-134]] | Asaas BR payment integration | [ ] | backend |
| [[BCN-135]] | Endpoint `GET /v1/billing/usage-mtd` + `GET /v1/billing/invoices` | [ ] | backend |
| [[BCN-136]] | UI BeaconBilling.tsx wiring backend | [ ] | frontend |

## Phase 13 — Frontend wiring (consumir API real)

UI tem **19 pages mocks** prontas. Wiring backend real conforme cada
endpoint estiver pronto.

| ID | Título | Status | Owner |
|---|---|---|---|
| [[BCN-150]] | OpenAPI codegen TypeScript client | [ ] | frontend |
| [[BCN-151]] | Wiring `BeaconOverview.tsx` → `/v1/overview` | [ ] | frontend |
| [[BCN-152]] | Wiring `BeaconMessages.tsx` → `/v1/messages` (list + filter) | [ ] | frontend |
| [[BCN-153]] | Wiring `BeaconTemplates.tsx` → `/v1/templates/*` | [ ] | frontend |
| [[BCN-154]] | Wiring `BeaconJourneys.tsx` → `/v1/journeys/*` | [ ] | frontend |
| [[BCN-155]] | Wiring `BeaconSuppression.tsx` → `/v1/suppression` | [ ] | frontend |
| [[BCN-156]] | Wiring `BeaconDomains.tsx` → `/v1/domains` | [ ] | frontend |
| [[BCN-157]] | Wiring `BeaconSmsNumbers.tsx` → `/v1/sms-numbers` | [ ] | frontend |
| [[BCN-158]] | Wiring `BeaconWhatsapp.tsx` → `/v1/whatsapp` | [ ] | frontend |
| [[BCN-159]] | Wiring `BeaconPushApps.tsx` → `/v1/push-apps` | [ ] | frontend |
| [[BCN-160]] | Wiring `BeaconWebhooks.tsx` → `/v1/webhooks` | [ ] | frontend |
| [[BCN-161]] | Wiring `BeaconAnalytics.tsx` → `/v1/analytics/messages` | [ ] | frontend |
| [[BCN-162]] | Wiring `BeaconApiKeys.tsx` → `/v1/api-tokens` | [ ] | frontend |
| [[BCN-163]] | Wiring `BeaconLgpd.tsx` → `/v1/audit/lgpd/dsar` | [ ] | frontend |
| [[BCN-164]] | Wiring `BeaconBilling.tsx` → `/v1/billing/*` | [ ] | frontend |
| [[BCN-165]] | Wiring `BeaconChain.tsx` (visualização audit chain BLAKE3) | [ ] | frontend |
| [[BCN-166]] | Wiring `BeaconDeliverability.tsx` (Postal reputation) | [ ] | frontend |
| [[BCN-167]] | Wiring `BeaconAntispam.tsx` (ML score per tenant) | [ ] | frontend |
| [[BCN-168]] | Wiring `BeaconSettings.tsx` + `BeaconTeam.tsx` | [ ] | frontend |

## Phase 14 — Cluster Fase 3 handoff

| ID | Título | Status | Owner |
|---|---|---|---|
| [[BCN-180]] | ExternalSecret CRDs `secret/rewire/beacon/*` (Vault paths) | [ ] | infra |
| [[BCN-181]] | Authentik OIDC client `beacon-ui` configurado | [ ] | infra |
| [[BCN-182]] | Kong route `app.beacon.rewirelabs.dev` + `api.beacon.rewirelabs.dev` | [ ] | infra |
| [[BCN-183]] | ServiceMonitor + OTLP exportar para PULSE-CLOUD | [ ] | infra |
| [[BCN-184]] | NetworkPolicies ingress permitido cross-product ver [[ADR-0005]] | [ ] | infra |
| [[BCN-185]] | MinIO buckets `beacon-evidence` + `beacon-templates-assets` | [ ] | infra |
| [[BCN-186]] | Backup Postgres `beacon` schema + ClickHouse retention | [ ] | infra |

## Phase 15 — Tests + smoke

| ID | Título | Status | Owner |
|---|---|---|---|
| [[BCN-200]] | Coverage 70%+ control plane Python | [ ] | qa |
| [[BCN-201]] | Smoke E2E: criar org → token → send email → check delivery → verify chain | [ ] | qa |
| [[BCN-202]] | Load test 1000 RPS endpoint `/v1/messages/email` (locust) | [ ] | qa |
| [[BCN-203]] | Deliverability test: enviar para Mail Tester + verificar score >9/10 | [ ] | qa |
| [[BCN-204]] | RLS isolation tests cross-tenant | [ ] | qa |

## Phase 16 — Documentação

| ID | Título | Status | Owner |
|---|---|---|---|
| [[BCN-220]] | `docs/00-overview.md` (similar Admin/App pattern) | [ ] | docs |
| [[BCN-221]] | `docs/02-architecture.md` diagrama camadas | [ ] | docs |
| [[BCN-222]] | `docs/runbooks/email-ip-warmup.md` | [ ] | docs |
| [[BCN-223]] | `docs/runbooks/postal-incident.md` | [ ] | docs |
| [[BCN-224]] | `docs/runbooks/anti-spam-false-positive.md` | [ ] | docs |
| [[BCN-225]] | `docs/runbooks/dsar-export-deadline.md` (LGPD 15d) | [ ] | docs |
| [[BCN-226]] | `docs/cluster-integration/` (5 docs equivalentes outros services) | [ ] | docs |
| [[BCN-227]] | OpenAPI spec dump em `docs/api/openapi.yaml` + CI check | [ ] | backend |

## Convenções

- IDs `BCN-XXX` monotonicamente crescentes
- Cross-reference `[[BCN-XXX]]` ou `[[ADR-XXXX]]`
- Marcar `[x]` após PR merged + smoke pass
- Beacon depende de outros produtos (CONNECT, FOUNDRY, HOST, AUDIT-TRAIL,
  GUARDIAN) — sinalizar dependência explícita em `Pré-requisitos`

# REWIRE-NOTIFY / BEACON — Notification Platform multi-canal

> **Disambiguação**: V0.1 = **rewire-notify** (Telegram dispatcher interno, `@RewireLabsBot`). V0.2 = **BEACON** (Notification Platform multi-canal BR comercial, evolução do notify).

## Identidade

| Campo | Valor |
|---|---|
| **Nome V0.1** | rewire-notify (slug `notify`) — uso interno |
| **Nome V0.2** | BEACON (marketing externo) — produto comercial |
| **Categoria** | Communications / Notifications |
| **Maturidade V0.1** | Em produção (Telegram bot ativo) |
| **Maturidade V0.2** | Em design — 24 tickets em 6 phases |
| **Slug** | `/produtos/beacon` (V0.2) |
| **Localização do código** | `services/rewire-notify/` |

---

## O que faz

### V0.1 — Dispatcher interno (atual)

Dispatcher de notificações operacionais do cluster Rewire via **Telegram Bot API** (`@RewireLabsBot`). Substitui Slack `#cluster-team` legacy. Endpoints:

- `/alerts/telegram` — Alertmanager webhook intake (HMAC)
- `/events` — Direct event POST (producers sem Redpanda)
- Consume `cluster.events.global` Redpanda topic
- Daily digest 09:00 BRT via APScheduler
- Bot commands: `/status`, `/daily`, `/alerts`, `/help`

**12 event kinds suportados**: tenant.onboarded, asaas.payment_received, product.crashloop, vault.sealed, breach.detected, tenant.hard_cap_exceeded, lgpd.dsar.requested, foundry.pr.merged, daily.summary, smoke.test.failed, cost.anomaly, pricing.change.applied.

**Routing rules**:
- `critical` → operator private chat (push priority) + group
- `warn`/`info` → group only (silent)
- 4 kinds sempre escalam (vault.sealed, breach.detected, product.crashloop, smoke.test.failed)

### V0.2 — BEACON (multi-canal comercial)

Evolução para plataforma de notificações **multi-canal BR** em API única:

- **Email** (Postal 3.x self-hosted)
- **SMS** (Zenvia / TotalVoice — parceria BR)
- **WhatsApp** (via produto CONNECT da Rewire)
- **Push mobile** (APNs + FCM)
- **Push web** (VAPID)
- **Telegram** (continua suportado)

**Pricing**: per-notification por canal + Free quota. NF-e Asaas BR. Substitui Twilio/SendGrid/Pusher/Mandrill para mercado BR com pricing previsível em real.

---

## Stack

### V0.1 atual

| Camada | Tecnologia |
|---|---|
| **Backend** | FastAPI 0.115+ Python 3.13 |
| **Dispatcher** | Telegram Bot API |
| **Event intake** | Alertmanager webhook + Redpanda consumer + direct POST |
| **Scheduler** | APScheduler |
| **Config** | ExternalSecret via Vault (`kv/rewire/notify/telegram-*`) |
| **Deploy** | Helm `deploy/helm/rewire-notify/` + ApplicationSet wave 5 (observability ns) |

### V0.2 BEACON adicional

| Camada | Tecnologia |
|---|---|
| **Email server** | Postal 3.x (self-hosted, OSS) |
| **SMS BR** | Zenvia / TotalVoice (parceria, REST API) |
| **WhatsApp** | CONNECT API (produto Rewire futuro) |
| **Push mobile** | APNs (Apple) + FCM (Google) |
| **Push web** | VAPID + Service Worker |
| **Analytics** | ClickHouse 24.x (event analytics, retention 90d) |
| **Billing** | Lago integration (consents + opt-outs + per-channel) |
| **Audit** | AUDIT-TRAIL anchora consents + opt-outs (LGPD) |
| **Templates** | Bilingue PT-BR / EN-US, variables typed |
| **Distributed lock** | Redis (multi-pod idempotency) |

---

## Casos de uso

### V0.1 (interno cluster)
1. **Alertmanager critical** dispara → Telegram operator + group push
2. **Tenant onboarded** evento → digest diário 09:00 BRT
3. **Asaas payment received** → notify cluster-team automatic
4. **FOUNDRY PR merged** → bot comment

### V0.2 (BEACON comercial)
1. **Cliente E-commerce BR** envia transactional emails (pedido confirmado, NF-e gerada) via BEACON SMS + email
2. **Cliente HealthTech** envia lembretes consulta via WhatsApp + push mobile com fallback SMS
3. **Cliente FinTech** envia 2FA via SMS BR + LGPD opt-out fluxo nativo
4. **App ASCEND-generated** consome BEACON SDK pra todas notificações
5. **Customer support Rewire** notifica clientes via BEACON multi-canal sem precisar integrar 5 providers

---

## Conectividade cross-produto

| Produto | Como conecta |
|---|---|
| **CONNECT** | BEACON usa CONNECT como camada WhatsApp Business |
| **AUDIT-TRAIL** | Anchora consents + opt-outs (LGPD strict) |
| **NOVA Gateway** | Geração inteligente de templates (V0.5+: AI-generated content per audience) |
| **CITADEL chain** | Eventos críticos (breach.detected) audited imediato |
| **GUARDIAN** | Notify de alertas SIEM via BEACON multi-canal |
| **PULSE-CLOUD** | Métricas (events/min, error rate per channel, opt-out rate) |
| **LAGO** | Billing per-channel per-tenant |
| **AUTHENTIK** | OIDC + consent management per user |
| **ASCEND** | Apps gerados consomem `@rewirelabs/beacon-sdk` |
| **FOUNDRY** | PRs notificam stakeholders via BEACON |
| **TODOS produtos cluster** | Produzem eventos para `cluster.events.*` Redpanda → BEACON dispatcher |

---

## Diferencial vs mercado

| Concorrente | O que faz | Diferencial BEACON |
|---|---|---|
| **Twilio** | SMS + WhatsApp + voice — global player | BEACON é **BR-first** (NF-e, real, Zenvia parceria), integrado cluster |
| **SendGrid / Mailgun** | Email transactional global | BEACON é **multi-canal único API**, NF-e, LGPD nativo |
| **OneSignal** | Push notifications grátis com limites | BEACON é **integrated multi-canal**, pricing previsível, LGPD opt-out |
| **Pusher / Ably** | Realtime + notifications | BEACON foca em **persistent notifications**, não realtime stream |
| **Mandrill** | Email transactional Mailchimp | BEACON cobre todos canais BR, sem dependência Mailchimp |

---

## Pipeline de desenvolvimento (6 phases · 24 tickets)

- **Phase 0** — Bootstrap: scaffold FastAPI + Telegram adapter
- **Phase 1** — Foundation: webhook intake, Kafka consumer, producer events cross-product, helm config
- **Phase 2** — Control plane: daily digest real, bot status 18 products, rate limit
- **Phase 3** — BEACON V0.2: Postal email, multi-pod lock, ClickHouse, Authentik consent, Zenvia SMS, CONNECT WhatsApp
- **Phase 4** — Deploy: APNs/FCM push mobile, VAPID push web, Lago billing, helm hardening
- **Phase 5** — Compliance: AUDIT-TRAIL anchor consents, LGPD DSAR flow, Prometheus exporter, template bilingue

Detalhes: [docs/tickets/README.md](docs/tickets/README.md).

---

## Resumo executivo

**rewire-notify (V0.1)** é o dispatcher Telegram interno atual do cluster Rewire — `@RewireLabsBot` recebe 12 event kinds de Alertmanager + Redpanda + direct POST, dispara para operator + group conforme severity. **BEACON (V0.2)** é a evolução comercial: notification platform multi-canal BR (email Postal + SMS Zenvia + WhatsApp CONNECT + push APNs/FCM/VAPID) em API única, com billing per-channel via Lago, NF-e BR, LGPD consent management nativo, e analytics ClickHouse. Substitui Twilio + SendGrid + OneSignal para mercado brasileiro.

---

**Versão**: 2026-05-23 v0.1 (executive overview).

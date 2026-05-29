# MESSAGING

> **Notification platform multi-canal BR (email + SMS + WhatsApp + push iOS/Android/web + Telegram). Umbrella (consolida ex-notify + ex-beacon). 78% código / 8% beacon — em PRODUÇÃO desde 2026-05-18.**

**Hostname**: `messaging.rewirelabs.dev`, `beacon.rewirelabs.dev` (legacy redirect)
**Repository**: `services/rewire-messaging/`
**Status**: 78% código (notify funcional) / 8% beacon (scaffold). Deployment down ~10h pelo P0 sistêmico (image dev-latest aguardando build pos-consolidação)
**Canonical helm chart**: `architecture/products/messaging/helm/`
**ADRs relevantes**: 0108 C2 (consolida notify+beacon → messaging), 0042 (audit canonical webhook standards)
**Last updated**: 2026-05-25
**Fontes**: `services/RESUMO.md` §3.6, `services/rewire-messaging/BEACON.md` (legacy spec preservada), `docs/futuros_produtos/audits/REWIRE-BEACON_AUDIT.md`, `REWIRE-NOTIFY_AUDIT.md`

---

## O que é

MESSAGING é a plataforma unificada de notificações transacionais e marketing-light multi-canal da Rewire. **API única** para email + SMS + WhatsApp Business + push mobile (iOS + Android) + push web + Telegram interno.

**Tagline**: "SendGrid + Twilio + OneSignal substituídos por uma única API BR. Email + SMS + WhatsApp + push em real, com NF-e, audit chain BLAKE3 e LGPD nativo. Pricing 40-60% abaixo dos gringos."

**Histórico**: Pós-ADR 0108 C2 consolida 2 produtos legacy:
- `rewire-notify` (interno funcional — produção 2026-05-18)
- `rewire-beacon` (scaffold push/SMS — spec V0)

Resultado: produto único `rewire-messaging` cobrindo TODOS canais. Hostname legacy `beacon.rewirelabs.dev` mantido como redirect para `messaging.rewirelabs.dev` (compat clientes antigos).

Spec autoritativa pré-consolidação preservada em `services/rewire-messaging/BEACON.md` (1008 linhas) para referência histórica de decisões V0 (Postal 3.x escolha + Zenvia parceria + Kafka queue + MJML template framework etc).

## Funcionalidades core

### Email transacional

- **Primário**: Postal 3.x self-hosted (MIT) — 8 servidores Postal (3 primary + 5 workers) com pool 60 IPs BR
- **Fallback alto volume**: AWS SES sa-east-1 (Scale+ tier, >500k/mês ou bursts >100k/dia)
- DKIM signing automático por domínio cliente (CNAME + chave 2048-bit)
- SPF assistance + DMARC reporting agregado
- Reputation management auto (warm-up 30 dias novos IPs)
- Templates MJML 5.x + react-email preview UI

### SMS BR

- **Primário**: Parceria Zenvia (revenue-share 15-25%)
- **Fallback**: TotalVoice
- Cobertura nacional Vivo/TIM/Claro/Oi
- Markup transparente ao cliente

### WhatsApp Business

- Via produto CONNECT (rewire-connect) — MESSAGING faz REST call internal `/connect/internal/v1/whatsapp/send`
- CONNECT abstrai BSP layer (Take Blip primary V0/V1, Cloud API V2+)
- Templates Meta UI + sessions 24h

### Push notifications

- **iOS**: APNs integração direta (grátis Apple)
- **Android**: FCM direto (grátis Google)
- **Web**: VAPID + Service Worker (Web Push Protocol RFC 8030 W3C)

### Telegram interno

- @RewireLabsBot — notificações operacionais cluster team
- Dispatcher V0.1 funcional

### Workflows multi-step

- Temporal 1.25+ workflows: "email; se não abrir em 24h, SMS; se não responder em 48h, WhatsApp"
- A/B testing nativo
- Anti-spam ML preventivo (bloqueia tenant mass-spam pattern)
- Suppression list cross-canal unified per organization (opt-out email = opt-out SMS/WA/push)

### Compliance

- Audit chain CITADEL por mensagem (hash BLAKE3 conteúdo + recipient + timestamp + lawful basis)
- LGPD DSAR endpoint + lawful basis tag por mensagem
- Breach notification 3-day automation
- Multi-tenant strict (Postal virtual hosts per org + Kafka topics per tenant + ClickHouse DBs per tenant)

## Stack técnica

- **Language**: Python 3.13 FastAPI 0.115+
- **Database**: Postgres CNPG 17 schema `messaging`
- **Cache**: Redis 7.4
- **Email MTA**: Postal 3.x (MIT) self-hosted + AWS SES sa-east-1 fallback
- **SMS**: Zenvia API (primary) + TotalVoice (fallback)
- **WhatsApp**: via CONNECT API internal
- **Push iOS**: APNs cert (direct Apple)
- **Push Android**: FCM key (direct Google)
- **Push web**: VAPID keys + SW
- **Telegram**: @RewireLabsBot (interno)
- **Queue**: Apache Kafka (Strimzi) + RabbitMQ retry/DLQ
- **Workflow**: Temporal 1.25+
- **Analytics**: ClickHouse 24.x (bilhões msgs) + TimescaleDB ops metrics
- **Templates**: MJML 5.x + react-email preview
- **Anti-spam ML**: scikit-learn + sentence-transformers (semantic similarity)
- **Auth**: Authentik OIDC + API tokens per tenant
- **Secrets**: OpenBao/Vault (API keys SMS/SES/APNs/FCM)
- **Image**: `192.168.1.110:30500/rewire-labs/rewire-messaging-control-plane:dev-latest`

## Integrações cross-product Rewire

| Serviço | Como usa |
|---|---|
| **CONNECT** | WhatsApp channel via REST internal `/connect/internal/v1/whatsapp/send` |
| **CITADEL chain** | Forense por mensagem (BLAKE3 anchor) |
| **SECURITY/GUARDIAN** | Alert notification target |
| **AUDIT** | Compliance evidence (LGPD lawful basis) |
| **FOUNDRY** | Templates (FOUNDRY templates BEACON-aware) |
| **SERVERS (ex-HOST)** | Apps SDK envio transacional |
| **ASCEND** | Cross-sell apps gerados embarcam MESSAGING SDK |
| **Authentik** | OIDC backbone |
| **OpenBao/Vault** | Secrets (API keys SMS/SES/APNs/FCM) |
| **SENTINEL** | Test failure notifications |
| **rewire-app** | Transactional emails (welcome/invoice/payment) |
| **rewire-admin** | Operator notifications (cluster events) |

## Concorrentes externos (mercado)

**Email**:
- SendGrid (Twilio) USD $19,95-$249/mês + IOF
- AWS SES direto sem multi-canal
- Postal direto sem multi-tenant

**SMS**:
- Twilio Programmable Messaging
- Zenvia BR (caro datado)
- TakeBlip

**Push**:
- OneSignal
- Braze
- MessageBird

Diferencial Rewire: uma única API + UI + billing + NF-e para TODOS canais, em real, audit chain por mensagem, pricing 40-60% abaixo dos gringos.

## Pricing (proposta)

**Tiered por volume mensal (email/SMS/push) + WhatsApp pass-through**

| Canal | Modelo |
|---|---|
| **Email** | Tiered Hobby R$97 → Scale R$2.000+. Postal IPs dedicados Scale+ |
| **SMS** | Markup ~30% sobre Zenvia/TotalVoice (~R$0,06-0,09 → R$0,07-0,12/SMS) |
| **WhatsApp** | Pass-through Meta + 30% markup (utility R$0,12-0,18 / marketing R$0,30-0,50 / auth R$0,12-0,15) |
| **Push iOS/Android/web** | Tiered por volume (grátis APNs/FCM/VAPID) — markup infra/multi-tenant |
| **NF-e** | Asaas BR automatizado |

**Comparação SendGrid**: USD $19,95/mês mínimo + IOF; MESSAGING R$97/mês com NF-e — 40-60% mais barato.

**CapEx refactor `rewire-notify` interno → multi-tenant**: R$60k (3 meses dev) + IPs dedicados Postal R$200-400/IP/mês colocation reputation building.

## Estado de implementação V0

**78% código (ex-notify funcional) / 8% beacon (ex-beacon scaffold)**

- ✅ ex-notify em PRODUÇÃO desde 2026-05-18 (Telegram dispatcher V0.1 + email basic)
- ❌ Deployment down ~10h pelo **P0 sistêmico do cluster** (image dev-latest aguardando build pos-consolidação ex-notify + ex-beacon)
- ❌ SMS Zenvia integration (V0.2 MVP backlog)
- ❌ Push iOS/Android/web (V0.2 MVP backlog)
- ❌ Anti-spam ML preventivo (V0.3 backlog)
- ❌ ClickHouse analytics (V0.4 backlog)
- ❌ Workflows multi-step Temporal (V0.5 backlog)

## Próximos passos (roadmap)

- **V0.1 (unblock)**: Build + push imagem dev-latest registry + redeploy
- **V0.2**: SMS Zenvia integration + Push APNs/FCM/VAPID
- **V0.3**: Anti-spam ML preventivo (scikit-learn + sentence-transformers)
- **V0.4**: ClickHouse analytics (bilhões msgs)
- **V0.5**: Workflows Temporal multi-step ("se não abrir email → SMS")
- **V1**: A/B testing nativo + suppression list cross-canal unified
- **V2**: Voice calling (BSP parceria)

**ARR target ano 3**: R$8M

## Documentação relacionada

- ADR 0108 C2 — Consolida rewire-notify + rewire-beacon → rewire-messaging
- ADR 0042 — Webhook standards canonical + audit chain
- Audit doc BEACON: `docs/futuros_produtos/audits/REWIRE-BEACON_AUDIT.md`
- Audit doc NOTIFY: `docs/futuros_produtos/audits/REWIRE-NOTIFY_AUDIT.md`
- Spec legacy (preservada): `services/rewire-messaging/BEACON.md` (1008 linhas — decisões V0 push/SMS)
- Spec atual: `services/rewire-messaging/README.md`
- RESUMO: `services/RESUMO.md` §3.6

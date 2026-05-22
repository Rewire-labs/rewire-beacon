# BEACON — Notification Platform Multi-Canal BR

> **Spec autoritativa do produto** — extraida de `rewire_cluster/docs/futuros_produtos/`.
> Mantida no root do repo do produto pra implementadores nao precisarem cross-repo lookup.
> Quando mudar, atualizar AMBOS lados (single-source-of-truth do produto continua
> sendo o monorepo `rewire_cluster`).

---

## 2 · BEACON — Notification Platform Multi-Canal BR

> **Status**: planejamento (pré-implementação, base interna `rewire-notify` aproveitada)
> **Owner**: cluster team + comercial
> **Escopo**: API única para email (Postal self-hosted + AWS SES BR fallback) + SMS (parceria Zenvia/TotalVoice BR) + WhatsApp (via CONNECT) + push iOS/Android (APNs/FCM direto) + push web (VAPID). Pricing em real, NF-e automática, audit chain CITADEL por mensagem, LGPD nativo com cross-channel unsubscribe.
> **Não-objetivos V0**: substituir SendGrid em volume enterprise globalmente (foco BR mid-market), oferecer voice calling (V2+), oferecer fax (nunca), oferecer email marketing pesado com templates designers studio (foco transacional + light marketing), substituir BSP WhatsApp direto sem CONNECT (BEACON usa CONNECT como camada WhatsApp).
> **Localização do código**: novo repo `Rewire-labs/rewire-beacon` (refactor do `rewire-notify` interno para multi-tenant production-grade)
> **Localização dos manifests cluster**: `rewire_cluster/architecture/beacon/` + `services/rewire-beacon/`
> **Localização da infra**: control plane + Postal MTAs + workers no cluster Rewire SP; AWS SES sa-east-1 como fallback; SMS via API parceiros; WhatsApp via CONNECT API
> **Versionamento**: SemVer independente (`beacon vX.Y.Z`)

### 2.0 — Decisões fechadas

| # | Decisão | Resposta | Implicação técnica |
|---|---|---|---|
| 1 | Email server primário | **Postal 3.x** self-hosted (MIT) | Open source maduro, gestão de IPs próprios, reputation management, DKIM/SPF/DMARC automático |
| 2 | Email server fallback alto volume | **AWS SES sa-east-1** (não white-label, apenas infra resiliente) | Para clientes Scale+ que precisam de >1M emails/mês sem queimar reputation dos IPs Postal |
| 3 | Email template framework | **MJML 5.x** (MIT) + react-email para preview UI | MJML é padrão para emails responsivos cross-client |
| 4 | SMS BR | **Parceria revenue-share Zenvia (primary) + TotalVoice (fallback)** | BSPs BR oficiais com cobertura nacional Vivo/TIM/Claro/Oi; revenue share 15-25% |
| 5 | SMS internacional | **Twilio** (apenas se cliente explicitamente pedir, V1+) | BR é foco V0 |
| 6 | WhatsApp Business | **Integração com CONNECT** quando lançado (Q3 2026) | Não duplicar trabalho; CONNECT é o BSP layer |
| 7 | Push mobile iOS | **APNs (Apple Push Notification service) integração direta** (grátis) | Direto Apple, sem intermediário |
| 8 | Push mobile Android | **FCM (Firebase Cloud Messaging) direto** (grátis) | Direto Google, sem intermediário |
| 9 | Push web | **VAPID + Service Worker** (Web Push Protocol RFC 8030) | Padrão W3C, suporta Chrome/Firefox/Edge/Safari |
| 10 | Queue de envio | **Apache Kafka (Strimzi)** + RabbitMQ para retry + dead letter | Kafka para throughput alto (10k+ msgs/s); RabbitMQ para workflows complexos |
| 11 | Workflow multi-step | **Temporal 1.25+** | Workflows tipo "email; se não abrir em 24h, SMS; se não responder em 48h, WhatsApp" |
| 12 | Backend API | **FastAPI 0.115+** (Python 3.13) + PostgreSQL 17 + Redis 7.4 | Pattern Rewire |
| 13 | Analytics (events bilhões de mensagens) | **ClickHouse 24.x** (Apache 2.0) + TimescaleDB para metrics ops | ClickHouse para queries analytics escaláveis |
| 14 | Anti-spam ML | **Custom Python services + scikit-learn + sentence-transformers para semantic similarity** | Detectar uso suspeito por cliente (mass-spam pattern, content suspeito) |
| 15 | Suppression list | **Cross-canal unified per organization** | Usuário opt-out de email vale para SMS, WhatsApp, push do mesmo cliente |
| 16 | Audit chain | **CITADEL chain** — cada mensagem tem hash BLAKE3 (conteúdo + recipient + timestamp + consent basis) | Compliance LGPD audit-by-default |
| 17 | LGPD | **DSAR endpoint + lawful basis tag por mensagem + breach notification 3-day** | Diferencial cross-product Rewire |
| 18 | Identity | **Authentik OIDC** + API tokens per tenant (REST API consumers) | Pattern Rewire |
| 19 | Secrets | **OpenBao/VAULT-BR** (API keys SMS providers, SES credentials, APNs certs, FCM keys) | Reuso cluster |
| 20 | Multi-tenant isolation | **Postal virtual hosts per organization + Kafka topics per tenant + ClickHouse databases per tenant** | Tenant data nunca cruza |
| 21 | Pricing model | **Tiered por volume mensal (email/SMS/push) + WhatsApp pass-through** | Previsibilidade vs SendGrid USD per-volume |
| 22 | Pagamento | **Asaas BR** + NF-e automática | Pattern Rewire |
| 23 | Suporte | **PT-BR developer-focused** | Email transacional é developer-driven; comunidade Slack/Discord |
| 24 | Reuso `rewire-notify` interno | **SIM — refactor para production-grade multi-tenant** (2-3 meses economizados) | Base interna já funciona; precisa hardening + billing + UI |
| 25 | Integração nativa Rewire | **FOUNDRY (templates BEACON-aware) + HOST (apps SDK) + AUDIT TRAIL (compliance evidence) + GUARDIAN (alert notification) + CONNECT (WhatsApp channel)** | Cross-product moat |

**Decisões adicionais explicitadas**:

- **CapEx menor que GUARDIAN** — usa stack existente (Postal já roda interno como `rewire-notify`). Investimento principal é em IPs dedicados para email (custo ~R$ 200-400 por IP/mês em colocation com reputation building) e em integração com Zenvia/TotalVoice (acordo comercial).
- **NÃO operamos próprios servidores SMS** — parceria com Zenvia/TotalVoice. Eles têm gateway com operadoras Vivo/TIM/Claro/Oi. Markup transparente ao cliente.
- **WhatsApp depende de CONNECT** — BEACON envia mensagem WhatsApp via REST call para CONNECT API interna; CONNECT abstrai BSP parceiro
- **Anti-spam preventivo** — ML detecta padrão de uso suspeito por tenant (cliente novo enviando 100k emails em 1h para lista comprada) e BLOQUEIA preventivamente, alertando customer success
- **Deliverability é o killer feature** — IP reputation management cuidadoso + DKIM/SPF/DMARC + bounce handling + complaint loop processing. Postal entrega 98%+ se configurado certo

### 2.1 — Pitch comercial

**Tagline**: "SendGrid + Twilio + OneSignal substituídos por uma única API BR. Email + SMS + WhatsApp + push em real, com NF-e, audit chain BLAKE3 e LGPD nativo. Pricing 40-60% abaixo dos gringos."

Plataforma unificada de notificações transacionais e marketing-light multi-canal: email, SMS, WhatsApp Business, push mobile (iOS + Android), e push web. Construída sobre Postal (email), parcerias com Zenvia/TotalVoice (SMS BR), integração com CONNECT (WhatsApp), e APNs/FCM (push). Diferencial absoluto: **uma única API + UI + billing + NF-e para todos os canais, em real, com audit chain por mensagem enviada**.

### 2.2 — Produto detalhado

#### 2.2.1 Email transacional

**Postal self-hosted no cluster**:
- Pool de 8 servidores Postal (3 primary, 5 workers) com pool de 60 IPs públicos brasileiros (~10 IPs/Postal node)
- Reputation management automático: novo IP entra em warm-up 30 dias (ramp gradual)
- DKIM signing automático por domínio do cliente (cliente adiciona CNAME, Postal gera chave 2048-bit)
- SPF assistance: validação SPF do cliente, sugestão de records corretos
- DMARC reporting: agregação de DMARC reports recebidos, dashboard customer

**AWS SES sa-east-1 como fallback**:
- Para clientes Scale+ com volumes >500k/mês ou bursts >100k/dia
- Não white-label SES (cliente precisa de email "@" próprio domínio)
- Custo passado direto + markup 30%

**Templates HTML responsivos**:
- Editor visual MJML-based (UI com preview iOS/Android/Outlook/Gmail/Apple Mail)
- Variáveis Handlebars-like: `{{customer_name}}`, `{{order_number}}`, etc
- Conditional blocks: `{{#if is_premium}}...{{/if}}`
- Loops para listas: `{{#each items}}...{{/each}}`
- Templates marketplace: 50+ templates prontos (e-commerce order confirmation, password reset, welcome email, magic link, etc)

**A/B testing nativo**:
- Variant A vs B em 5%/95%, 50%/50%, etc
- Métricas: open rate, click rate, conversion (via webhook callback)
- Decisão automática winner após N envios

**Bounce/complaint handling**:
- Hard bounces auto-add para suppression list (cross-canal)
- Soft bounces: retry exponential backoff (4 tentativas em 24h)
- Complaints (recipient marked as spam) → permanent suppression
- Webhook bidirecional para cliente saber em real-time

**Tracking**:
- Open rate (pixel tracking opcional, opt-in pelo cliente para compliance LGPD)
- Click rate (link rewriting tracking)
- Unsubscribe rate
- Complaint rate
- Bounce rate por tipo (hard/soft/block/auto-response)

#### 2.2.2 SMS

**Parceria revenue-share Zenvia (primary) + TotalVoice (fallback)**:
- Cobertura nacional Vivo/TIM/Claro/Oi
- Short codes (5 dígitos) para alto volume Scale+
- Long codes (números 11 dígitos) para PMEs
- Two-way SMS (recebimento de respostas) — webhook para cliente
- Tracking: delivered (entregue ao MSC), failed, undelivered, blocked
- Limite anti-spam configurável por cliente (default: 1 SMS/segundo, ramp up baseado em histórico)

**Pricing pass-through + markup transparente**:
- Custo Zenvia/TotalVoice: ~R$ 0,06-0,09 por SMS BR
- BEACON cobra: R$ 0,07-0,12 por SMS (markup ~30%)
- Cliente vê: "1.000 SMS = R$ 70-120"

#### 2.2.3 WhatsApp Business

**Integração nativa com CONNECT** (quando lançado):
- BEACON é cliente do CONNECT API interna
- REST call: `POST /connect/internal/v1/whatsapp/send` com tenant context
- CONNECT abstrai BSP parceiro (Take Blip / Zenvia / Sinch) ou Cloud API direto (V2+)
- Templates aprovados pelo WhatsApp gerenciados via UI BEACON (sync com CONNECT)
- Janelas 24h gerenciadas pelo CONNECT
- Quality rating compartilhado

#### 2.2.4 Push mobile (iOS + Android)

**APNs (Apple Push Notification service) integração direta**:
- Cliente faz upload do APNs certificate ou usa token-based auth (.p8)
- BEACON gerencia connection pool + retry + bad device token cleanup
- Suporte a rich notifications (imagens, vídeos, ações)
- Silent push para sync background

**FCM (Firebase Cloud Messaging) integração direta**:
- Cliente faz upload do Service Account JSON do projeto Firebase
- BEACON gerencia HTTP/2 connection + retry + topic management
- Suporte a data messages + notification messages
- Topic subscription management

**Funcionalidades comuns push**:
- Segmentação por device, plataforma, app version, geo (IP-based), custom attributes (key-value)
- Rich notifications: imagens, ações, deep links
- A/B testing (variant A vs B)
- Tracking: delivered, opened, action taken (via SDK BEACON ou callback custom)
- SDK iOS (Swift) + Android (Kotlin) + React Native + Flutter (V0.5+)

#### 2.2.5 Push web (browser)

**Web Push Protocol (RFC 8030) com VAPID**:
- Service Worker setup automatizado (BEACON fornece JS snippet)
- Suporte Chrome 50+, Firefox 44+, Edge 17+, Safari 16+
- VAPID keys gerenciadas pelo BEACON (cliente não precisa gerar)
- Encryption end-to-end (Chrome/Firefox suportam Aes128Gcm)

#### 2.2.6 Funcionalidades cross-canal

**Workflows multi-step (Temporal)**:
- "Envia email; se não abrir em 24h, envia SMS; se não responder em 48h, envia WhatsApp; se não responder em 7d, marca lead frio"
- Visual flow builder UI (similar n8n)
- Wait activities com signals
- Conditional branching

**Routing inteligente**:
- Cliente pode definir preferência de canal por usuário (`preferred_channel: ["whatsapp", "email", "sms"]`)
- BEACON tenta na ordem; fallback se canal não disponível ou bouncing

**Quiet hours**:
- Respeitar horários por timezone do recipient
- Default: não enviar SMS/push entre 22h-7h local time
- Configurável por organização

**Frequency capping**:
- Máximo N notificações por usuário por dia (configurável)
- Cross-canal (todos os canais contam para o limite)
- Prevenção de "notification fatigue"

**Unsubscribe centralizado**:
- Link único de unsubscribe que vale para TODOS os canais
- Cliente acessa página, vê todos os canais opted-in, pode unsubscribe individual ou de todos
- Compliance LGPD Art. 18 (direito ao opt-out)

**Webhooks bidirecionais**:
- Cliente recebe eventos em tempo real: `message.sent`, `message.delivered`, `message.opened`, `message.clicked`, `message.unsubscribed`, `message.bounced`, `message.complained`
- Retry exponential backoff com 24h max
- Signing HMAC-SHA256 para verificação

#### 2.2.7 Diferenciais Rewire

1. **API única para 5 canais**: cliente integra uma vez, usa todos. Concorrentes globais vendem APIs separadas (SendGrid email + Twilio SMS + Twilio WA + OneSignal push = 4 SDKs)

2. **Pricing em real, NF-e automática**: SendGrid USD $19,95/mês mínimo + IOF; BEACON R$ 97/mês com NF-e

3. **Audit chain CITADEL por mensagem**: cada notificação tem hash forense (conteúdo + recipient + timestamp + consent basis tag) — diferencial absoluto para auditoria LGPD provando consentimento

4. **LGPD nativo**: lawful basis tags, DSAR endpoints, suppression list cross-canal, breach notification 3-day automático

5. **Suporte PT-BR engineering**: time entende contexto BR (ANATEL, regras WhatsApp Business BR, operadoras)

6. **Integração ecosystem Rewire**: FOUNDRY (templates BEACON-aware por padrão em código gerado), HOST (apps integram em 1 linha SDK), AUDIT TRAIL (eventos para compliance evidence), CONNECT (WhatsApp), GUARDIAN (alert notification)

7. **Anti-spam inteligente**: ML detecta uso suspeito (cliente tentando spam) e bloqueia preventivamente — protege reputação coletiva dos IPs Postal

8. **Reuso `rewire-notify` interno**: base de código já existe e funciona em produção interna; transformar em produto é trabalho de UI multi-tenant + billing + segmentação

### 2.3 — Stack open source consolidado

| Camada | Tecnologia | Licença | Versão | Justificativa |
|---|---|---|---|---|
| **Email server** | Postal | MIT | 3.x | Maduro, gestão IPs próprios |
| **Email server alternativa** | Stalwart Mail Server | AGPL | 0.10+ | Roadmap V1+; mais moderno que Postal |
| **Email template framework** | MJML | MIT | 5.x | Padrão emails responsivos |
| **Email preview UI lib** | react-email | MIT | 3.x | Preview + editing |
| **Queue throughput alto** | Apache Kafka (Strimzi) | Apache 2.0 | 3.9+ | Multi-tenant topics |
| **Queue workflow / DLQ** | RabbitMQ | MPL 2.0 | 4.x | Retry, dead letter |
| **Workflow orchestration** | Temporal | MIT | 1.25+ | Multi-step durable workflows |
| **Backend API** | FastAPI | MIT | 0.115+ | Pattern Rewire |
| **Backend runtime** | Python | PSF | 3.13 | Pattern Rewire |
| **Database (transactional)** | PostgreSQL | PostgreSQL | 17 | Pattern Rewire |
| **Database (analytics events)** | ClickHouse | Apache 2.0 | 24.x | Bilhões de eventos query-friendly |
| **Cache / rate limiting** | Redis | BSD-3 | 7.4 | Pattern Rewire |
| **Anti-spam ML** | scikit-learn + sentence-transformers + spaCy | BSD-3 / Apache 2.0 / MIT | latest | Detection padrão suspeito |
| **APNs library** | aioapns | Apache 2.0 | latest | Async APNs client |
| **FCM library** | aiohttp + Google Cloud Python | Apache 2.0 | latest | Async FCM client |
| **Web Push library** | pywebpush | MPL 2.0 | latest | RFC 8030 |
| **Observability** | OpenTelemetry Collector | Apache 2.0 | latest | PULSE-CLOUD shared |
| **Identity** | Authentik | MIT | 2026.3+ | Cluster service |
| **Secrets** | OpenBao | MPL 2.0 | 2.5+ | Cluster service |
| **Audit chain** | CITADEL (Rewire) | proprietary | latest | Cross-product reuse |

### 2.4 — ICP primário e secundário

#### ICP primário

1. **SaaS B2B BR** (todos precisam de email transacional + push notifications)
   - Ticket esperado: R$ 297-2.997/mês
2. **E-commerce BR** (notificações order/shipping/abandoned cart via email + SMS + WhatsApp + push)
   - Ticket esperado: R$ 1.497-9.997/mês
3. **Fintechs/bancos digitais** (alertas transação via SMS + WhatsApp + push)
   - Ticket esperado: R$ 4.997-29.997/mês
4. **Healthtechs** (lembretes consulta, resultados via SMS + WhatsApp + email)
   - Ticket esperado: R$ 997-7.997/mês
5. **Marketplaces BR** (comunicação comprador-vendedor)
   - Ticket esperado: R$ 1.997-14.997/mês
6. **Apps mobile BR** (push para engagement e retention)
   - Ticket esperado: R$ 497-4.997/mês

#### ICP secundário

7. **Agências digitais BR** (revenda para clientes finais — white-label V1+)
8. **Empresas com app interno** (notificações para funcionários — RH, comunicados)

### 2.5 — Concorrentes

**Globais**:
- **SendGrid (Twilio)**: padrão mercado email transacional. $19,95-$249/mês + tiers, USD. **Posicionamento BEACON**: 40-60% mais barato em real + multi-canal único + NF-e
- **Twilio Programmable Messaging**: SMS + WhatsApp + chat. USD. **Posicionamento**: multi-canal + LGPD + BR
- **Mailgun**: email transacional, similar SendGrid. **Posicionamento**: mesmo
- **Amazon SES**: barato $0,10/1000 emails mas DIY, USD. **Posicionamento**: managed completo + multi-canal
- **Postmark**: email premium, USD. **Posicionamento**: mesmo preço, multi-canal
- **OneSignal**: push leader (free tier + premium), USD. **Posicionamento**: multi-canal único
- **Braze, Iterable**: marketing automation enterprise, $$$$ USD. **Posicionamento**: foco transacional + light marketing
- **MessageBird (Bird)**: omnichannel europeu, USD/EUR. **Posicionamento**: BR-first vs Europa-first

**Brasileiros**:
- **Zenvia**: omnichannel BR, sólido mas API antiga e UI datada. **Possível parceiro SMS** (acordo revenue share)
- **TotalVoice**: SMS + voz BR, API decente. **Possível parceiro SMS** (fallback)
- **TakeBlip**: WhatsApp + chatbots, foco messaging. **Concorre via CONNECT**, complementar para BEACON
- **Pluggy**: comunicação para fintechs. **Posicionamento**: mais geral, multi-vertical
- **Octadesk, Movidesk**: helpdesk + comunicação. **Posicionamento**: foco notification, não helpdesk
- **Locaweb Mail Marketing**: legado. **Posicionamento**: API moderna + multi-canal
- **Gap absoluto**: zero "API única multi-canal moderno em real" BR. **Este é o gap que BEACON preenche**

### 2.6 — Pricing model Rewire detalhado

| Tier | Email/mês | SMS/mês | Push/mês | WhatsApp/mês | Domain senders | A/B testing | Workflows | Preço/mês |
|---|---|---|---|---|---|---|---|---|
| **Hobby** | 10k | 1k | 5k | — | 1 | — | — | R$ 97 |
| **Starter** | 100k | 10k | 100k | 5k | 3 | ✅ | — | R$ 497 |
| **Growth** | 1M | 100k | 1M | 50k | 5 | ✅ | ✅ | R$ 1.997 |
| **Scale** | 10M | 1M | 10M | 500k | Ilimitado | ✅ | ✅ | R$ 7.997 |
| **Enterprise** | Volumes acima | Volumes acima | Volumes acima | Volumes acima | + Dedicated IP + SLA 99,99% + CSM | ✅ | ✅ | R$ 19.997-99.997 |

**Overage**:
- Email: R$ 1,50 por 1000 (vs SendGrid USD $0,80 ≈ R$ 4)
- SMS: R$ 0,07-0,12 por mensagem (vs Twilio USD $0,0075 ≈ R$ 0,04 mas BR cobertura $)
- WhatsApp: conforme tabela Meta + markup 30% (utility ~R$ 0,12-0,18, marketing ~R$ 0,30-0,50)
- Push mobile (APNs/FCM): R$ 0,01 por 1000 (custo Apple/Google = grátis, cobramos pelo overhead)
- Push web (VAPID): R$ 0,01 por 1000

**Add-ons**:
- **Dedicated IP** (email): R$ 297/mês cada (warmup managed)
- **Dedicated WhatsApp number**: R$ 497/mês cada
- **Custom integration** (cliente SaaS específico, ERP): R$ 4.997 one-time + R$ 297/mês
- **White-label** (agência): R$ 9.997 setup + R$ 1.497/mês

### 2.7 — Schema PostgreSQL completo (DDL)

```sql
-- ============================================================
-- Schema: tenants e usuários
-- ============================================================

CREATE SCHEMA tenancy;

CREATE TABLE tenancy.organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    cnpj VARCHAR(18) UNIQUE NOT NULL,
    razao_social VARCHAR(500) NOT NULL,
    industry_segment VARCHAR(100),
    plan_tier VARCHAR(50) NOT NULL DEFAULT 'hobby',
    plan_started_at TIMESTAMPTZ,
    monthly_quota_email INTEGER DEFAULT 10000,
    monthly_quota_sms INTEGER DEFAULT 1000,
    monthly_quota_push INTEGER DEFAULT 5000,
    monthly_quota_whatsapp INTEGER DEFAULT 0,
    current_period_start DATE NOT NULL,
    current_period_end DATE NOT NULL,
    suspended BOOLEAN DEFAULT FALSE,
    suspended_reason VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- Schema: sender domains e configurações
-- ============================================================

CREATE SCHEMA senders;

CREATE TABLE senders.email_domains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES tenancy.organizations(id),
    domain VARCHAR(255) NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    dkim_selector VARCHAR(50) DEFAULT 'beacon',
    dkim_public_key TEXT,
    dkim_private_key_vault_path VARCHAR(255),
    spf_record_suggested TEXT,
    spf_verified BOOLEAN DEFAULT FALSE,
    dmarc_record_suggested TEXT,
    dmarc_verified BOOLEAN DEFAULT FALSE,
    dedicated_ip_id UUID, -- nullable, only Scale+
    reputation_score INTEGER, -- 0-100 from Postal
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(organization_id, domain)
);

CREATE TABLE senders.dedicated_ips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES tenancy.organizations(id),
    ip_address INET NOT NULL UNIQUE,
    warmup_started_at TIMESTAMPTZ,
    warmup_completed_at TIMESTAMPTZ,
    current_daily_limit INTEGER DEFAULT 1000,
    reputation_score INTEGER,
    status VARCHAR(20) DEFAULT 'warming', -- 'warming', 'active', 'blocked'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE senders.whatsapp_numbers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES tenancy.organizations(id),
    phone_number VARCHAR(20) NOT NULL,
    connect_number_id UUID NOT NULL, -- FK para CONNECT
    quality_rating VARCHAR(20), -- 'green', 'yellow', 'red'
    messaging_limit_tier VARCHAR(20), -- 'tier_1k', 'tier_10k', 'tier_100k', 'tier_unlimited'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(organization_id, phone_number)
);

CREATE TABLE senders.push_apps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES tenancy.organizations(id),
    name VARCHAR(255) NOT NULL,
    platform VARCHAR(20) NOT NULL, -- 'ios', 'android', 'web'
    bundle_id VARCHAR(255), -- iOS bundle id ou Android package
    apns_cert_vault_path VARCHAR(255), -- iOS only
    apns_team_id VARCHAR(50),
    apns_key_id VARCHAR(50),
    fcm_service_account_vault_path VARCHAR(255), -- Android only
    vapid_public_key TEXT, -- Web only
    vapid_private_key_vault_path VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- Schema: templates
-- ============================================================

CREATE SCHEMA templates;

CREATE TABLE templates.email_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES tenancy.organizations(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    subject_template TEXT NOT NULL, -- Handlebars-like
    mjml_source TEXT NOT NULL,
    html_compiled TEXT, -- compiled cache
    plain_text_template TEXT,
    variables_schema JSONB DEFAULT '{}'::jsonb, -- expected variables for validation
    category VARCHAR(50), -- 'transactional', 'marketing', 'security', 'system'
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE templates.sms_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES tenancy.organizations(id),
    name VARCHAR(255) NOT NULL,
    body_template TEXT NOT NULL, -- Handlebars-like, max 160 chars (or 70 if unicode)
    is_unicode BOOLEAN DEFAULT FALSE,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE templates.push_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES tenancy.organizations(id),
    name VARCHAR(255) NOT NULL,
    title_template TEXT NOT NULL,
    body_template TEXT NOT NULL,
    image_url_template TEXT,
    deep_link_template TEXT,
    actions JSONB DEFAULT '[]'::jsonb,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- Schema: suppression list cross-canal
-- ============================================================

CREATE SCHEMA suppression;

CREATE TABLE suppression.entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES tenancy.organizations(id),
    identifier_type VARCHAR(20) NOT NULL, -- 'email', 'phone', 'device_token', 'user_id'
    identifier_value TEXT NOT NULL,
    channels_blocked JSONB NOT NULL DEFAULT '[]'::jsonb, -- ['email', 'sms', 'whatsapp', 'push']
    reason VARCHAR(50) NOT NULL, -- 'user_unsubscribed', 'hard_bounce', 'complaint', 'manual', 'dpo_request'
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ, -- nullable, permanent if NULL
    notes TEXT,
    UNIQUE(organization_id, identifier_type, identifier_value)
);

CREATE INDEX idx_supp_org_id ON suppression.entries(organization_id, identifier_type, identifier_value);

-- ============================================================
-- Schema: webhooks
-- ============================================================

CREATE SCHEMA webhooks;

CREATE TABLE webhooks.endpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES tenancy.organizations(id),
    name VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    events JSONB NOT NULL DEFAULT '[]'::jsonb, -- ['message.sent', 'message.delivered', etc]
    signing_secret_vault_path VARCHAR(255) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    retries_max INTEGER DEFAULT 24,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE webhooks.deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    endpoint_id UUID NOT NULL REFERENCES webhooks.endpoints(id),
    event_type VARCHAR(50) NOT NULL,
    related_message_id UUID,
    payload JSONB NOT NULL,
    attempt_count INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    last_response_status INTEGER,
    last_response_body TEXT,
    next_retry_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'pending' -- 'pending', 'delivered', 'failed_permanent'
);

CREATE INDEX idx_webhook_delivery_pending ON webhooks.deliveries(status, next_retry_at) WHERE status = 'pending';

-- ============================================================
-- Schema: providers (SMS BSPs)
-- ============================================================

CREATE SCHEMA providers;

CREATE TABLE providers.sms_provider_routes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    country_code VARCHAR(5) NOT NULL,
    primary_provider VARCHAR(50) NOT NULL, -- 'zenvia', 'totalvoice', 'twilio'
    fallback_provider VARCHAR(50),
    cost_per_sms_brl DECIMAL(10,4) NOT NULL,
    margin_percent DECIMAL(5,2) DEFAULT 30.0,
    enabled BOOLEAN DEFAULT TRUE
);
```

### 2.8 — ClickHouse schema (event analytics)

```sql
-- Database: beacon_events

CREATE TABLE messages (
    organization_id UUID,
    message_id UUID,
    channel String, -- 'email', 'sms', 'whatsapp', 'push_ios', 'push_android', 'push_web'
    template_id Nullable(UUID),
    sender_id UUID, -- email domain, sms number, push app, whatsapp number
    recipient_identifier String, -- email, phone, device token
    recipient_user_id Nullable(String), -- internal user id
    sent_at DateTime64(3) DEFAULT now64(3),
    delivered_at Nullable(DateTime64(3)),
    opened_at Nullable(DateTime64(3)),
    clicked_at Nullable(DateTime64(3)),
    bounced_at Nullable(DateTime64(3)),
    complained_at Nullable(DateTime64(3)),
    unsubscribed_at Nullable(DateTime64(3)),
    failed_at Nullable(DateTime64(3)),
    failure_reason String,
    lawful_basis_tag String, -- 'consent', 'contract', 'legal_obligation', 'legitimate_interest'
    content_hash String, -- BLAKE3 hash for audit chain
    citadel_chain_hash String,
    cost_brl_billed Decimal64(6),
    provider_used String, -- 'postal', 'aws_ses', 'zenvia', 'totalvoice', 'apns', 'fcm', 'webpush', 'connect_whatsapp'
    metadata Map(String, String)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(sent_at)
ORDER BY (organization_id, sent_at, message_id)
TTL sent_at + INTERVAL 13 MONTH;

CREATE TABLE message_events (
    organization_id UUID,
    message_id UUID,
    event_type String, -- 'sent', 'delivered', 'opened', 'clicked', 'bounced', 'complained', 'unsubscribed', 'failed'
    event_at DateTime64(3) DEFAULT now64(3),
    metadata Map(String, String)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_at)
ORDER BY (organization_id, message_id, event_at)
TTL event_at + INTERVAL 13 MONTH;

-- Materialized views for fast dashboards
CREATE MATERIALIZED VIEW daily_stats_by_org_channel
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(day)
ORDER BY (organization_id, day, channel)
AS SELECT
    organization_id,
    toDate(sent_at) AS day,
    channel,
    count() AS sent_count,
    countIf(delivered_at IS NOT NULL) AS delivered_count,
    countIf(opened_at IS NOT NULL) AS opened_count,
    countIf(clicked_at IS NOT NULL) AS clicked_count,
    countIf(bounced_at IS NOT NULL) AS bounced_count,
    countIf(complained_at IS NOT NULL) AS complained_count,
    sum(cost_brl_billed) AS total_cost_brl
FROM messages
GROUP BY organization_id, day, channel;
```

### 2.9 — Workflows Temporal (esqueleto)

```python
# services/rewire-beacon/python/beacon/workflows/multichannel_journey.py

from temporalio import workflow
from datetime import timedelta

@workflow.defn
class MultiChannelJourneyWorkflow:
    """
    Workflow para journeys multi-canal complexos.
    Exemplo: 'Envia email; se não abrir em 24h, SMS; se não responder em 48h, WhatsApp'
    """

    @workflow.run
    async def run(self, journey_config: dict) -> dict:
        """
        journey_config = {
            'organization_id': '...',
            'recipient': {'email': '...', 'phone': '...', 'user_id': '...'},
            'steps': [
                {'type': 'send_email', 'template_id': '...', 'wait_for_event': 'opened', 'wait_timeout_hours': 24},
                {'type': 'send_sms', 'template_id': '...', 'wait_for_event': 'replied', 'wait_timeout_hours': 48},
                {'type': 'send_whatsapp', 'template_id': '...', 'wait_for_event': 'replied', 'wait_timeout_hours': 168},
                {'type': 'mark_cold_lead'}
            ],
            'context_variables': {'order_id': '12345', 'customer_name': 'João'}
        }
        """
        org_id = journey_config['organization_id']
        recipient = journey_config['recipient']
        variables = journey_config['context_variables']

        for step in journey_config['steps']:
            # Check if unsubscribed before each step
            is_suppressed = await workflow.execute_activity(
                "check_suppression",
                {"org_id": org_id, "recipient": recipient, "channel": step['type'].replace('send_', '')},
                schedule_to_close_timeout=timedelta(seconds=5),
            )

            if is_suppressed:
                workflow.logger.info(f"Recipient suppressed for {step['type']}, stopping journey")
                break

            # Execute step
            if step['type'].startswith('send_'):
                channel = step['type'].replace('send_', '')
                message_result = await workflow.execute_activity(
                    f"send_message_{channel}",
                    {"org_id": org_id, "template_id": step['template_id'],
                     "recipient": recipient, "variables": variables,
                     "lawful_basis": step.get('lawful_basis', 'consent')},
                    schedule_to_close_timeout=timedelta(seconds=30),
                    retry_policy=workflow.RetryPolicy(maximum_attempts=3),
                )

                # Wait for event with timeout
                if step.get('wait_for_event'):
                    try:
                        event_received = await workflow.wait_condition(
                            lambda: self._event_received(message_result['id'], step['wait_for_event']),
                            timeout=timedelta(hours=step['wait_timeout_hours']),
                        )
                        if event_received:
                            workflow.logger.info(f"Event {step['wait_for_event']} received, stopping journey")
                            return {"completed_step": step['type'], "outcome": "engaged"}
                    except TimeoutError:
                        workflow.logger.info(f"Timeout waiting for {step['wait_for_event']}, continuing")

            elif step['type'] == 'mark_cold_lead':
                await workflow.execute_activity(
                    "mark_lead_status",
                    {"org_id": org_id, "user_id": recipient['user_id'], "status": "cold"},
                    schedule_to_close_timeout=timedelta(seconds=5),
                )

        return {"completed_step": "all", "outcome": "no_engagement"}
```

### 2.10 — Endpoints REST principais (OpenAPI)

```yaml
openapi: 3.1.0
info:
  title: BEACON API
  version: 0.1.0
servers:
  - url: https://api.beacon.rewirelabs.dev/v1

paths:
  /messages/email:
    post:
      summary: Send email
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [from, to, subject]
              properties:
                from: {type: string, format: email}
                to: {oneOf: [{type: string}, {type: array, items: {type: string}}]}
                cc: {type: array, items: {type: string}}
                bcc: {type: array, items: {type: string}}
                reply_to: {type: string}
                subject: {type: string}
                html_body: {type: string}
                text_body: {type: string}
                template_id: {type: string, format: uuid}
                template_variables: {type: object}
                attachments: {type: array, items: {type: object}}
                headers: {type: object}
                tags: {type: array, items: {type: string}}
                lawful_basis: {type: string, enum: [consent, contract, legal_obligation, legitimate_interest]}
                tracking: {type: object, properties: {opens: {type: boolean}, clicks: {type: boolean}}}
      responses:
        '202': {description: Accepted for delivery}

  /messages/sms:
    post:
      summary: Send SMS
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [from, to, body]
              properties:
                from: {type: string}
                to: {type: string} # E.164 format
                body: {type: string}
                template_id: {type: string, format: uuid}
                template_variables: {type: object}
                lawful_basis: {type: string}

  /messages/whatsapp:
    post:
      summary: Send WhatsApp message (via CONNECT)

  /messages/push:
    post:
      summary: Send push notification (mobile or web)
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                app_id: {type: string, format: uuid}
                to: {oneOf: [{type: object, properties: {device_tokens: {type: array, items: {type: string}}}}, {type: object, properties: {topic: {type: string}}}, {type: object, properties: {user_ids: {type: array, items: {type: string}}}}]}
                title: {type: string}
                body: {type: string}
                image_url: {type: string}
                deep_link: {type: string}
                actions: {type: array}
                template_id: {type: string, format: uuid}

  /messages/{message_id}:
    get:
      summary: Get message status

  /messages/{message_id}/events:
    get:
      summary: Get event timeline for message

  /journeys:
    post:
      summary: Start multi-channel journey

  /journeys/{journey_id}:
    get:
      summary: Get journey status

  /domains:
    get:
    post:
      summary: Register email domain

  /domains/{domain_id}/verify:
    post:
      summary: Verify domain DNS records

  /templates/email:
    get:
    post:

  /templates/sms:
    get:
    post:

  /suppression:
    get:
      summary: List suppressed identifiers
    post:
      summary: Add identifier to suppression list

  /webhooks:
    get:
    post:

  /analytics/messages:
    get:
      summary: Aggregate analytics (delivered, opened, clicked rates)
      parameters:
        - name: channel
          in: query
          schema: {type: string}
        - name: from
          in: query
          schema: {type: string, format: date}
        - name: to
          in: query
          schema: {type: string, format: date}
        - name: group_by
          in: query
          schema: {type: string, enum: [day, hour, template]}

  /audit/lgpd/dsar:
    post:
      summary: LGPD DSAR — return all messages for a data subject
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                identifier_type: {type: string, enum: [email, phone, user_id]}
                identifier_value: {type: string}
```

### 2.11 — Arquitetura completa (diagrama ASCII)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                  BEACON — Arquitetura completa                                    │
└──────────────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────┐
  │  Clientes (Apps, Sites,  │
  │  Backends, Workflows)   │
  └────────┬────────────────┘
           │ REST API / SDK
           ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │              BEACON Cluster (cluster Rewire SP)                  │
  │                                                                  │
  │  ┌────────────────────────────────────────────────────────────┐ │
  │  │  REST API Gateway (FastAPI + Authentik OIDC + API tokens) │ │
  │  └─────────────────────────┬──────────────────────────────────┘ │
  │                            │                                     │
  │                            ▼                                     │
  │  ┌────────────────────────────────────────────────────────────┐ │
  │  │  Rate Limiter + Quota Manager (Redis)                      │ │
  │  └─────────────────────────┬──────────────────────────────────┘ │
  │                            │                                     │
  │                            ▼                                     │
  │  ┌────────────────────────────────────────────────────────────┐ │
  │  │  Suppression Check (Postgres) + Frequency Cap (Redis)      │ │
  │  └─────────────────────────┬──────────────────────────────────┘ │
  │                            │                                     │
  │                            ▼                                     │
  │  ┌────────────────────────────────────────────────────────────┐ │
  │  │  Anti-Spam ML Check (Python service)                       │ │
  │  └─────────────────────────┬──────────────────────────────────┘ │
  │                            │                                     │
  │                            ▼                                     │
  │  ┌────────────────────────────────────────────────────────────┐ │
  │  │  Template Render (MJML compile + Handlebars vars)          │ │
  │  └─────────────────────────┬──────────────────────────────────┘ │
  │                            │                                     │
  │                            ▼                                     │
  │  ┌────────────────────────────────────────────────────────────┐ │
  │  │  Audit Chain Anchor (CITADEL POST /chain/append)           │ │
  │  └─────────────────────────┬──────────────────────────────────┘ │
  │                            │                                     │
  │                            ▼                                     │
  │  ┌────────────────────────────────────────────────────────────┐ │
  │  │  Kafka Producer → topic beacon.send.{channel}.{tier}       │ │
  │  └─────────┬───────────────┬───────────────┬─────────┬────────┘ │
  │            │               │               │         │          │
  │            ▼               ▼               ▼         ▼          │
  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────┐ │
  │  │ Email Worker │ │ SMS Worker   │ │ Push Worker  │ │ WA W.  │ │
  │  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └────┬───┘ │
  │         │                │                │              │     │
  │         ▼                ▼                ▼              ▼     │
  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────┐ │
  │  │ Postal MTAs  │ │ Zenvia/Total │ │ APNs (Apple) │ │CONNECT │ │
  │  │ + AWS SES BR │ │  Voice APIs  │ │ FCM (Google) │ │  API   │ │
  │  │              │ │              │ │ WebPush svc  │ │        │ │
  │  └──────────────┘ └──────────────┘ └──────────────┘ └────────┘ │
  │         │                │                │              │     │
  │         │                │                │              │     │
  │         └────────────────┴────────────────┴──────────────┘     │
  │                                  │                              │
  │                                  ▼                              │
  │  ┌────────────────────────────────────────────────────────────┐ │
  │  │  Event Ingest (Postal webhooks, BSP webhooks, FCM/APNs    │ │
  │  │  responses, WebPush ACKs)                                  │ │
  │  └─────────────────────────┬──────────────────────────────────┘ │
  │                            │                                     │
  │                            ▼                                     │
  │  ┌────────────────────────────────────────────────────────────┐ │
  │  │  ClickHouse Event Store (bilhões de eventos)               │ │
  │  └─────────────────────────┬──────────────────────────────────┘ │
  │                            │                                     │
  │                            ▼                                     │
  │  ┌────────────────────────────────────────────────────────────┐ │
  │  │  Webhook Dispatcher (RabbitMQ + Python workers)            │ │
  │  │  → POST cliente endpoint com signing HMAC                  │ │
  │  └────────────────────────────────────────────────────────────┘ │
  │                                                                  │
  │  ┌────────────────────────────────────────────────────────────┐ │
  │  │  Temporal Workers (multi-channel journeys, A/B tests,      │ │
  │  │  scheduled campaigns, frequency cap reset, etc)            │ │
  │  └────────────────────────────────────────────────────────────┘ │
  └──────────────────────────────────────────────────────────────────┘

  Cross-product integrations:
  - FOUNDRY: golden paths geram código que usa BEACON SDK (Node, Python, Go)
  - HOST: apps em VMs HOST recebem BEACON SDK pré-instalado (cloud-init opcional)
  - AUDIT TRAIL: BEACON events fluem como compliance evidence
  - GUARDIAN: alertas críticos enviados via BEACON multi-canal
  - CONNECT: WhatsApp channel delegated to CONNECT API
  - SUPPORT: notifications dos tickets clientes enviadas via BEACON
```

### 2.12 — Integração cross-product detalhada

#### FOUNDRY → BEACON
- **Golden paths BEACON-aware**: templates Backstage incluem BEACON SDK init pré-configurado
- **Geração de código BEACON**: agentes FOUNDRY conhecem BEACON API e geram código de envio email/sms/push/whatsapp idiomatico
- **Marketplace de templates BEACON**: templates específicos para verticais (e-commerce, fintech, healthtech)

#### HOST → BEACON
- **SDK pré-instalado opcional**: VMs HOST com flag `--with-beacon-sdk` vêm com BEACON CLI + envvars configuradas
- **VM-level alerts**: BEACON pode ser usado por HOST para notificar customer sobre status VM (manutenção, etc)

#### AUDIT TRAIL → BEACON
- **Compliance evidence forwarding**: cada mensagem enviada com `lawful_basis` tag flui para AUDIT TRAIL como evidence
- **DSAR fulfillment**: AUDIT TRAIL consulta BEACON DSAR endpoint para retornar histórico de mensagens para data subject

#### GUARDIAN → BEACON
- **Critical alert notification**: alerts severity=critical do GUARDIAN são enviados via BEACON SMS + WhatsApp + push + email simultaneously
- **Incident communication**: incidents do GUARDIAN geram comunicações multi-canal para stakeholders

#### CONNECT → BEACON
- **WhatsApp channel**: BEACON delega envio WhatsApp para CONNECT API interna
- **Template sync**: templates WhatsApp aprovados Meta gerenciados em CONNECT, espelhados na UI BEACON
- **Quality rating**: visibilidade quality rating dos números compartilhada

#### SUPPORT → BEACON
- **Ticket notifications**: criação/update/resolução de tickets enviadas via BEACON (email + push + WhatsApp)
- **Custom rules**: SUPPORT pode definir routing rules ("ticket high severity → SMS para admin")

### 2.13 — CapEx e OpEx

**CapEx Fase MVP (mês 1-4)**:
- Refactor `rewire-notify` interno → BEACON multi-tenant: R$ 60k (3 meses dev)
- Postal infrastructure expansion (8 nodes 8c/16GB): R$ 35k
- IPs públicos brasileiros (60 IPs pool inicial): R$ 12k setup
- ClickHouse cluster (3 nodes 16c/64GB/4TB): R$ 28k
- UI Lovable + frontend customizado React: R$ 20k
- **Total CapEx MVP**: R$ 155k

**CapEx Fase GA (mês 5-8)**:
- AWS SES BR integration + dedicated IPs pool: R$ 15k
- Acordo Zenvia/TotalVoice (taxa setup + revenue share): R$ 10k
- Template marketplace dev (50 templates prontos): R$ 35k
- A/B testing engine + Temporal workflows: R$ 25k
- **Total CapEx GA**: R$ 85k

**CapEx Fase Enterprise (mês 12-18)**:
- WhatsApp integration via CONNECT (compartilhado): R$ 0 (cross-product)
- Dedicated IPs pool expansion (+100 IPs): R$ 20k
- ML anti-spam preventivo (Python services + training data labeled): R$ 45k
- White-label features (multi-tenant deep, custom branding): R$ 60k
- ISO 27001 + SOC 2 maintenance: R$ 30k (compartilhado com cluster)
- **Total CapEx Enterprise**: R$ 155k

**OpEx mensal steady state**:
- Postal IPs (60 IPs em colocation reputation building): R$ 15k
- AWS SES BR usage: R$ 8-15k (pass-through cliente)
- Zenvia/TotalVoice SMS: R$ 35-75k (pass-through cliente)
- ClickHouse storage growth: R$ 4k
- Customer success (1.5 FTE compartilhado): R$ 18k
- Sales alocação: R$ 12k
- **Total OpEx mensal**: R$ 92-130k

### 2.14 — Métricas-chave

- ARR ano 1: R$ 720k (120 clientes × R$ 500 médio)
- ARR ano 2: R$ 3,2M (450 clientes × R$ 600 médio + 20 Scale)
- ARR ano 3: R$ 8M (900 clientes × R$ 750 médio + 50 Scale + 10 Enterprise)
- Churn: <12% (transactional notifications são sticky; marketing notifications mais voláteis)
- Margem bruta: 50-65% (custo SMS via BSP, push grátis, email custo infra)
- Deliverability email: >98% (Postal + IP warming + reputation management)
- Latência envio: <2s do API call ao destinatário (P95)
- NPS target: >50 (developers gostam de API simples)

### 2.15 — Moat, Riscos, Esforço (síntese)

**Moat (síntese)**:
1. API única para 5 canais — nenhum concorrente BR tem isso unificado
2. Pricing em real, NF-e automática
3. Audit chain CITADEL por mensagem — único para LGPD audit
4. LGPD nativo cross-canal
5. Integração ecosystem Rewire (FOUNDRY, HOST, AUDIT TRAIL, CONNECT, etc)
6. Anti-spam ML coletivo
7. Suporte PT-BR engineering
8. Reuso `rewire-notify` interno acelera MVP

**Riscos**:
- SendGrid/Twilio agressivos em BR — improvável; mitigação NF-e + pricing real
- Margem SMS fina via BSP — Zenvia/TotalVoice dão 15-25%; mitigação positioning "tudo num lugar"
- WhatsApp depende CONNECT lançar primeiro — mitigação lançamento V0 sem WhatsApp
- Reputação IP queimada por cliente abusivo — mitigação ML anti-spam preventivo + IPs dedicados Scale+
- Concorrente BR Zenvia melhorar — mitigação API moderna + audit chain
- GDPR EU para exports — não cobrimos V0; roadmap V1+
- Anti-spam falso positivo — risco operacional; mitigação human review fast-track + whitelist managed

**Esforço**:
- **MVP** (3-4 meses): Postal + AWS SES fallback + push APNs/FCM + UI básica + billing + 30 design partners — **base `rewire-notify` reaproveitada economiza 2-3 meses**
- **GA** (6-8 meses): + SMS via Zenvia/TotalVoice + push web + templates editor MJML + A/B testing + 200 clientes pagantes
- **WhatsApp integration** (8-12 meses): integração com CONNECT (dependência); 50 clientes WhatsApp
- **Workflows multi-step e Enterprise** (12-18 meses): + Temporal + frequency capping cross-canal + dedicated IPs + SLA 99,99% + 500 clientes
- **White-label** (18-24 meses): multi-tenant deep + branding + reseller portal

---


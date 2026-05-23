# ADR 0005 — Integrações cross-product: FOUNDRY + HOST + AUDIT-TRAIL + GUARDIAN + CONNECT

> **Status**: Aceita
> **Data**: 2026-05-23
> **Autores**: Alessandro Queiroz + agente de documentação
> **Tags**: integrations, cross-product, ecosystem

## Contexto

BEACON.md §2.0 decisão 25 declara: **"Integração nativa Rewire: FOUNDRY
(templates BEACON-aware) + HOST (apps SDK) + AUDIT TRAIL (compliance
evidence) + GUARDIAN (alert notification) + CONNECT (WhatsApp channel)
— Cross-product moat"**.

BEACON.md §2.12 detalha cada integração mas falta formalizar **contrato
técnico** e **dependências** entre BEACON e os 5 produtos. Sem ADR
explícita, cada implementação ad-hoc cria débito acoplamento.

## Decisão

**Adotamos contratos técnicos versionados por integração** com 3 padrões
de comunicação:

### Padrão 1 — Server-to-server JWT m2m (síncrono)

Usado quando outro produto chama BEACON em runtime:

- **FOUNDRY → BEACON**: golden path code-gen consulta API BEACON para
  gerar SDK init code-snippets (raro, build-time)
- **HOST → BEACON**: VM cloud-init faz `POST /v1/api-tokens` para gerar
  token per VM com escopo limitado
- **GUARDIAN → BEACON**: alert critical dispara
  `POST /v1/messages/multi-channel` para enviar email+SMS+WA+push
  simultaneously
- **AUDIT-TRAIL → BEACON**: DSAR fulfillment consulta
  `POST /v1/audit/lgpd/dsar` para retornar histórico mensagens

**Autenticação**: JWT com `iss=rewire-<product>` validado por
`AuthentikJWTValidator` com `accepted_issuers` configurável
(ADR 0003).

### Padrão 2 — BEACON → outro produto (síncrono cliente)

- **BEACON → CONNECT** (WhatsApp): worker WhatsApp delega para
  `POST /connect/internal/v1/whatsapp/send` com tenant context
- **BEACON → AUDIT-TRAIL**: cada mensagem com `lawful_basis` emite
  evento via SDK Python BEACON (que internamente call AUDIT-TRAIL
  ingest)

**Autenticação**: BEACON emite JWT m2m com `iss=rewire-beacon` e usa
service-to-service flow

### Padrão 3 — Eventos assíncronos via Kafka/Redpanda

- **BEACON → CITADEL**: cada mensagem enviada publica em tópico
  `rewire.audit.chain.beacon.*` consumido por CITADEL chain backbone
  (BLAKE3 hash)
- **BEACON ← FOUNDRY**: templates BEACON-aware gerados pelo FOUNDRY
  publicam evento `foundry.template.created` consumido por BEACON
  marketplace
- **GUARDIAN ← BEACON**: eventos de delivery failure críticos
  (suppression cross-canal) publicam em tópico consumido por GUARDIAN
  para alertar customer success

## Justificativa

### Por que 3 padrões (não 1 universal)

- **Sincronismo**: alguns calls precisam resposta imediata (delivery
  status); outros podem ser eventually consistent (audit chain mirror)
- **Acoplamento**: HTTP sync acopla SLA; Kafka assíncrono desacopla
- **Use case driver**: GUARDIAN alert é "fire and wait briefly"; CITADEL
  mirror é "fire and forget eventually"

### Por que JWT m2m (não API tokens compartilhados)

- **Cluster ADR**: padrão Rewire cross-product
- **Scopes ricos**: JWT carrega claims (tenant context, scope) sem lookup
- **Auditável**: `iss` claim deixa claro quem chamou
- **Rotação centralizada**: Authentik provider config único

### Por que Kafka para audit mirror (não HTTP direto)

- **Disponibilidade**: BEACON não bloqueia se CITADEL fica down
- **Replay**: re-processar eventos para corrigir bug
- **Ordering**: Kafka partition por org garante mesmo recipient na
  mesma partition
- **Throughput**: Kafka absorve picos de envio massa

### Por que CONNECT-mediated WhatsApp (não BSP direto)

- **Quality rating**: CONNECT centraliza relacionamento BSP (Take Blip /
  Zenvia / Sinch); BEACON não duplica negociação contratual
- **Template approval**: WhatsApp templates aprovam pelo Meta via
  CONNECT (canonical); BEACON espelha na UI
- **24h window management**: CONNECT gerencia complexidade messaging
  windows; BEACON foca compose+send

## Consequências

### Positivas

- Cross-product moat real (diferencial vs SendGrid/Twilio que não têm
  ecossistema integrado)
- Dependências explícitas (cada integração documentada)
- BEACON desacoplado audit chain (CITADEL pode falhar sem afetar envio)
- WhatsApp delegado a especialista (CONNECT)
- Pattern reutilizável: outros produtos cluster adotam mesmo

### Negativas

- Dependência hard: WhatsApp channel só funciona quando CONNECT GA
  (Q3 2026 conforme BEACON.md decisão 6)
- 5 integrações = 5 contratos a versionar e manter
- Coordenação cross-team (FOUNDRY/HOST/AUDIT-TRAIL/GUARDIAN/CONNECT
  squads precisam alinhar)

### Neutras

- JWT m2m + Kafka topics são canonical cluster; sem custo adicional
- Volume de integração baixo na V0 (poucos clientes Enterprise)

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **Tudo HTTP síncrono** | Acoplamento alto; SLA cross-product |
| **Tudo Kafka assíncrono** | Latência inaceitável para GUARDIAN alert |
| **BEACON BSP WhatsApp direto** | Duplica esforço CONNECT; quality rating split |
| **API tokens compartilhados cross-product** | Sem auditabilidade `iss` |
| **gRPC para sync calls** | Overhead adoção; HTTP + JWT cobre 100% caso uso |

## Plano de implementação

(Maior parte é V0.3+ — depende dos produtos parceiros existirem)

### V0.1 (atual)

- [ ] Documentar interfaces em `docs/cluster-integration/00-overview.md`
- [ ] Network policy: ingress permitido de namespaces
  `rewire-foundry`, `rewire-host`, `rewire-audit-trail`,
  `rewire-guardian`, `rewire-connect`

### V0.2 — AUDIT-TRAIL + GUARDIAN integration

- [ ] Worker `audit_chain_mirror` consumindo Kafka topic
  `rewire.audit.chain.beacon.*`
- [ ] Cliente HTTP `integrations/audit_trail.py` para DSAR forwarding
- [ ] Cliente HTTP `integrations/guardian.py` para alert delivery

### V0.3 — CONNECT integration

- [ ] Worker WhatsApp delega para
  `integrations/connect.py::send_whatsapp`
- [ ] Template sync background job: pull aprovados Meta → mirror BEACON
  templates table

### V0.4 — FOUNDRY + HOST integration

- [ ] OpenAPI spec publicado em local conhecido (FOUNDRY consome para
  code-gen)
- [ ] HOST cloud-init script template includes BEACON SDK install + token
  provision

## Compliance e segurança

- JWT m2m: `iss` claim auditável via CITADEL chain
- Kafka topics: TLS in-flight + ACL Strimzi
- WhatsApp via CONNECT: LGPD compliance mantido (CONNECT é
  data-processor sob mesma DPA)
- DSAR cross-product: AUDIT-TRAIL agrega de N produtos (incluindo BEACON)

## Referências

- [BEACON.md §2.12 (integração cross-product detalhada)](../../BEACON.md)
- [BEACON.md §2.0 decisão 25](../../BEACON.md)
- ADR 0003 — Auth pattern (JWT m2m base)
- ADR 0002 — Data model split (Kafka como backbone)
- ADR cluster sobre cross-product communication patterns
- Specs de cada produto parceiro (FOUNDRY/HOST/AUDIT-TRAIL/GUARDIAN/CONNECT)

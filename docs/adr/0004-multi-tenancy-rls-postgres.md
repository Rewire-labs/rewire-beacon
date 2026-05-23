# ADR 0004 — Multi-tenancy via RLS Postgres + Postal virtual hosts + Kafka topics per tenant

> **Status**: Aceita
> **Data**: 2026-05-23
> **Autores**: Alessandro Queiroz + agente de documentação
> **Tags**: multi-tenancy, security, isolation

## Contexto

BEACON serve N organizações (clientes Hobby → Enterprise) no mesmo
cluster compartilhado. Dados sensíveis (mensagens transacionais,
recipients, payloads LGPD) **não podem** vazar entre tenants — fail =
multa ANPD + perda de cliente.

BEACON.md §2.0 decisão 20 estabelece "Multi-tenant isolation: Postal
virtual hosts per organization + Kafka topics per tenant + ClickHouse
databases per tenant. Tenant data nunca cruza."

Falta formalizar como isso é enforced em **cada camada do stack**.

## Decisão

**Adotamos isolamento defesa-em-profundidade em 4 camadas**:

### Camada 1 — Postgres (control plane)

- **RLS FORCE** em todas as tabelas multi-tenant (10+ tabelas)
- **GUC `beacon.current_org_id`** setado por middleware no início de
  cada request
- **POLICY `org_isolation`**: `USING (organization_id = current_setting('beacon.current_org_id')::uuid)`
- **Default deny**: GUC vazio = zero rows visíveis
- **Worker BYPASSRLS**: role separada para workers cross-org (analytics
  agregadas, billing reconciliação) com audit obrigatório

### Camada 2 — Postal (email server)

- **Virtual hosts per organization**: cada org tem seu virtual host
  Postal com config DKIM/SPF/DMARC isolada
- **API key per org**: BEACON worker autentica em Postal com credenciais
  da org
- **Domínio sender**: cada org pode adicionar seus próprios domínios
  verificados; sem cross-domain spoof

### Camada 3 — Kafka topics (event streaming)

- **Topic naming**: `beacon.send.<channel>.<tier>.<org_id>` para
  Enterprise OU `beacon.send.<channel>.<tier>` shared para Hobby/Starter
  com filtering downstream
- **ACL Kafka**: producers/consumers autorizados apenas para topics
  próprios via Strimzi KafkaUser CRDs
- **Encryption**: TLS in-flight + secrets per org criptografados em
  payload (Vault encryption-as-a-service)

### Camada 4 — ClickHouse (analytics)

- **Database per organization Enterprise**: `beacon_events_org_<uuid>`
  para isolamento total
- **Shared database para Hobby/Starter** com filtering por
  `organization_id` em queries + role per-org com view restricted
- **Row policies ClickHouse**: aplica filter automático ao query

## Justificativa

### Por que defesa-em-profundidade (não só RLS Postgres)

- **Blast radius**: comprometer RLS = leak dados control plane; mas
  emails ainda isolados em Postal vhost
- **Quality of service**: tenant Enterprise pode burnar IP reputation,
  mas tenants Hobby/Starter compartilhando IPs distintos não sofrem
- **Compliance**: clientes Enterprise BACEN exigem isolamento físico
  ou cryptographic comprovado

### Por que RLS FORCE Postgres (não app-side filter)

- **Defense in depth**: middleware bug = zero rows (não leak)
- **Postgres native**: padrão indústria + ferramentas auditor maduras

### Por que Postal virtual hosts (não shared MTA)

- **DKIM signing**: chave privada por org isolada
- **Reputation**: IP score Postal por vhost; tenant abusivo não afeta outros
- **Bounce handling**: bounces routed para webhook da org correta

### Por que Kafka ACLs (não apenas topic naming)

- **Defense in depth**: producer leak credencial = ainda não pode
  publicar em topic de outra org
- **Strimzi nativo**: KafkaUser CRD declarativo

### Por que ClickHouse database-per-org Enterprise (não shared)

- **Performance**: query Enterprise ~ms sem precisar filter row policy
- **Tenant offboard**: drop database trivial
- **Backup**: per-tenant retention diferenciado

### Por que shared ClickHouse Hobby/Starter

- **Cost**: 100s de databases ClickHouse seriam overhead
- **Volume baixo**: tenants pequenos cabem em shared sem performance hit
- **Row policy**: ClickHouse suporta nativo

## Consequências

### Positivas

- 4 camadas independentes de isolamento
- Compliance Enterprise garantida (BACEN/SOX-BR/LGPD)
- Tenant abusivo isolado (reputation, performance)
- Pattern Rewire RLS reusado

### Negativas

- Complexidade ops 4× maior (mitigação: tooling: Strimzi CRDs declarativos)
- ClickHouse database explosion potencial em GA com 1000+ Enterprise
  (mitigação: monitor + threshold migration para shared se necessário)
- Postal vhost provisioning é manual hoje (mitigação: automation
  workflow no V0.3)
- BYPASSRLS workers exigem audit rigoroso

### Neutras

- 10+ tabelas Postgres com RLS já no schema (BEACON.md §2.7)
- 7 anos LGPD retention split: Postgres 30d hot + S3 Glacier rest

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **DB-per-tenant Postgres** | Custo N× + cross-tenant impossível |
| **App-side filter sem RLS** | Bug = leak total |
| **Shared Postal sem vhosts** | Reputation cross-tenant; bounces misroute |
| **Shared Kafka topics filter app-side** | ACL fraca; vazamento credencial = leak |
| **ClickHouse shared 100% (sem split tier)** | Enterprise compliance fails |

## Plano de implementação

1. ✅ Migration `0001_initial.py` cria 5 tabelas iniciais com `tenant_id`
   (a expandir para `organization_id` canonical Rewire)
2. ⚠ Migration 0002 expand para 10+ tabelas conforme spec
3. ⚠ Migration 0003 aplica RLS FORCE + POLICY org_isolation em todas
4. ⚠ Migration 0004 cria role `beacon_worker` com BYPASSRLS
5. ⚠ Middleware `auth.py` extrai `org_id` do JWT/token, SET GUC
6. ⚠ Strimzi KafkaUser CRDs per org Enterprise
7. ⚠ Workflow Postal vhost provisioning per org
8. ⚠ ClickHouse provisioning script (database-per-org Enterprise +
   row policy shared Hobby/Starter)
9. ⚠ Tests `tests/rls/test_isolation.py` cobrindo 10+ tabelas
10. ⚠ Runbook `docs/runbooks/tenant-offboarding.md` (drop vhost +
    Kafka topics + ClickHouse DB)

## Compliance e segurança

- LGPD Art. 6 (segurança): isolamento físico cryptographic +
  RLS é evidência forte
- BACEN 4.658 (cybersecurity): defense in depth requirement
- ISO 27001 A.13.2.4 (segregação ambientes): atendido com 4 camadas
- Audit: cada query worker BYPASSRLS emite evento `worker.cross_tenant_query`

## Referências

- [BEACON.md §2.0 decisão 20 (multi-tenant isolation)](../../BEACON.md)
- [BEACON.md §2.7 schema completo](../../BEACON.md)
- ADR rewire-audit-trail/0006 — Multi-tenancy RLS + TimescaleDB (pattern)
- ADR rewire-admin/0003 — Tenancy model híbrido
- Strimzi KafkaUser CRD docs

# ADR 0002 — Data model split: PostgreSQL 17 transacional + ClickHouse 24 analytics

> **Status**: Aceita
> **Data**: 2026-05-23
> **Autores**: Alessandro Queiroz + agente de documentação
> **Tags**: data, database, analytics, multi-tenancy

## Contexto

BEACON precisa armazenar e consultar dois tipos muito distintos de dados:

### Tipo 1 — Transacional (Postgres-friendly)

- Organizações (tenants), users, memberships
- Templates de email/SMS/push (CRUD baixo volume)
- Domains email + DNS records + reputation
- SMS numbers, push apps
- Suppression list cross-canal (lookup por (org, identifier) crítico)
- Webhook endpoints + deliveries (status pending/delivered/failed)
- API tokens
- Quotas mensais por tenant
- Schema strongly-typed; JOINs frequentes; transactional ACID

### Tipo 2 — Event analytics (Postgres-unfriendly)

- Eventos de mensagens: `sent`, `delivered`, `opened`, `clicked`,
  `bounced`, `complained`, `unsubscribed`
- Volume projetado: **bilhões/ano** Enterprise (10M+ msgs/mês × 10
  events/msg médio = 100M+ events/mês)
- Queries analíticas: agregação por canal/dia/template/organização
- TTL: 13 meses de hot data; sumarizado depois
- Schema flexível (metadata per event_type varia)

## Decisão

**Adotamos data model split**: PostgreSQL 17 para Tipo 1 + ClickHouse 24.x
para Tipo 2.

Especificação:

### PostgreSQL 17 (`beacon` schema)

- **Cluster**: CNPG compartilhado cluster Rewire (não dedicado — escala
  do beacon control plane é compatível com pattern shared)
- **Multi-tenancy**: RLS FORCE com GUC `beacon.current_org_id` (mesmo
  pattern Admin/App)
- **Tabelas hot (~10 tabelas)**:
  - `tenancy.organizations` (já no schema spec)
  - `senders.email_domains`, `senders.dedicated_ips`,
    `senders.whatsapp_numbers`, `senders.push_apps`
  - `templates.email_templates`, `templates.sms_templates`,
    `templates.push_templates`
  - `suppression.entries` (index `(org, type, value)`)
  - `webhooks.endpoints`, `webhooks.deliveries`
  - `providers.sms_provider_routes` (config)
- **Connection pool**: PgBouncer transaction pooling
- **Backup**: WAL contínuo S3 + base daily; retention 30 dias hot + S3
  Glacier 7 anos (LGPD)

### ClickHouse 24.x (`beacon_events` database)

- **Cluster**: ClickHouse compartilhado cluster Rewire (3 nodes
  16c/64GB/4TB conforme BEACON.md §2.13 CapEx)
- **Multi-tenancy**: separação por database per organização Enterprise
  OU shared database com `organization_id` column para Hobby/Starter
  (decisão fina por tier)
- **Tabelas**:
  - `beacon_events.messages` (MergeTree, ORDER BY (org, sent_at, message_id))
  - `beacon_events.message_events` (eventos individuais)
  - `beacon_events.daily_stats_by_org_channel` (MaterializedView agregada)
- **Particionamento**: `toYYYYMM(sent_at)` (1 partition por mês)
- **TTL**: `sent_at + INTERVAL 13 MONTH` → drop automático
- **Compression**: ZSTD level 3 (ratio ~10×)

### Ingestão Postgres → ClickHouse

- **Kafka producer**: cada `POST /messages/*` enfileira evento
  em tópico Kafka `beacon.events.<channel>`
- **ClickHouse Kafka engine table** consome direto (sem ETL custom)
- **Latency**: < 5s do API call ao evento queryable em ClickHouse

## Justificativa

### Por que Postgres + ClickHouse (não tudo Postgres)

- **Performance analytics**: queries cross-message tipo "delivered rate
  por template último mês" rodam em ~ms em ClickHouse vs ~seconds em
  Postgres com 1B+ rows
- **Storage cost**: ClickHouse ZSTD level 3 → 10× menos disk que Postgres
- **TTL nativo**: ClickHouse drop chunks vencidos automático; Postgres
  precisaria pg_partman + custom cron
- **Postgres não-stresado**: 10 tabelas hot CRUD baixo volume rodam
  confortável em CNPG compartilhado

### Por que Postgres + ClickHouse (não tudo ClickHouse)

- **JOINs complexos**: org + memberships + templates + domains —
  Postgres é nativo
- **RLS multi-tenancy**: ClickHouse não tem RLS nativo (workaround
  via roles e views); Postgres pattern Rewire
- **Templates ACID**: edit template é transacional; ClickHouse
  eventual consistency não cabe

### Por que ClickHouse (não TimescaleDB)

- **Volume bilhões/ano**: ClickHouse escala 10-100× melhor para essa
  volumetria (Cloudflare, Uber, Mercado Libre confirmam)
- **MV aggregation**: ClickHouse MaterializedView com SummingMergeTree
  pre-agrega — perfeito para dashboards realtime
- **TimescaleDB OK até ~1B rows**, depois sofre

### Por que Kafka ingestão (não direct INSERT ClickHouse)

- **Buffer**: Kafka absorve pico de eventos (10k EPS sustainable
  ClickHouse direct INSERT degrada)
- **Replay**: re-processar eventos para corrigir bug analytics sem
  perda
- **Cross-product reuse**: Kafka já é canonical broker (alinha Redpanda
  cluster Rewire)

## Consequências

### Positivas

- Performance analytics excelente
- Storage cost otimizado
- TTL automático sem custom code
- Postgres transacional rápido
- Kafka buffer absorve picos
- Pattern reutilizável: outros produtos com analytics massivo (PULSE)
  podem replicar split

### Negativas

- 2 databases para operar (mitigação: ambos canonical cluster)
- Latência eventos: ~5s do API ao ClickHouse (aceitável para dashboards
  near-realtime; queries em Postgres não sofrem)
- Schema evolution duplo: mudar atributo de evento exige update em
  Kafka schema + ClickHouse + Postgres se referenciado
- Dev local: ClickHouse adiciona ~500MB container (vs Postgres só)

### Neutras

- Strimzi Kafka já no cluster; sem custo adicional
- Migrations Postgres seguem pattern Alembic schema-aware (`beacon`
  schema canonical)

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| **Tudo Postgres com partman** | Performance analytics ruim em 1B+ rows |
| **Tudo ClickHouse** | RLS multi-tenancy fraca; transacional ruim |
| **Postgres + TimescaleDB** | Não escala bilhões (BEACON volume) |
| **Postgres + InfluxDB** | InfluxDB push-based; sem MV agregação |
| **DynamoDB events + Postgres** | Vendor lock-in; viola soberania |
| **Postgres + Snowflake** | Snowflake SaaS pago caro; viola OSS-first |

## Plano de implementação

1. ✅ Migration `0001_initial.py` cria `beacon` schema com 5 tabelas básicas
2. ⚠ Expand migration: criar 10 tabelas conforme spec (senders,
   suppression, webhooks, providers)
3. ⚠ RLS FORCE + POLICY org_isolation em todas as tabelas multi-tenant
4. ⚠ ClickHouse cluster provisioning (Helm chart upstream)
5. ⚠ ClickHouse database `beacon_events` + tabelas + MV
6. ⚠ Kafka topics `beacon.events.<channel>` criados via Strimzi CRD
7. ⚠ ClickHouse Kafka engine table consumindo tópicos
8. ⚠ Endpoint `POST /messages/email` enfileira no Kafka (V0.2)
9. ⚠ Endpoint `GET /analytics/messages` (BEACON.md §2.10) query
   ClickHouse com cache Redis 5min
10. ⚠ Runbook `docs/runbooks/clickhouse-backfill.md`

## Compliance e segurança

- ClickHouse: encryption at rest (LUKS no PV); encryption in transit
  (TLS Kafka + ClickHouse)
- LGPD: DSAR endpoint consulta ambos Postgres + ClickHouse via worker
  background (BEACON.md §2.10)
- Right-to-be-forgotten: ClickHouse permite ALTER TABLE DELETE WHERE
  recipient_id = X (lento mas suportado); Postgres trivial

## Referências

- [BEACON.md §2.7 (Postgres DDL completo)](../../BEACON.md)
- [BEACON.md §2.8 (ClickHouse schema)](../../BEACON.md)
- [BEACON.md §2.0 decisão 13 (ClickHouse 24.x analytics)](../../BEACON.md)
- [docs/api/API_SPEC.md](../api/API_SPEC.md)
- ADR cluster sobre Redpanda/Kafka canonical broker

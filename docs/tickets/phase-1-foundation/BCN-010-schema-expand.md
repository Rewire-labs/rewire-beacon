# BCN-010 — Migration 0002 expandir schema para 10+ tabelas (senders, suppression, webhooks, providers)

**Owner**: backend
**Estimativa**: M (1d)
**Pré-requisitos**: nenhum (migration 0001 já criou 5 tabelas básicas)

## Definição

Expandir o schema `beacon` para incluir 10+ tabelas conforme spec
BEACON.md §2.7. Migration 0001 cobre só tabelas iniciais (tenants/channels/
templates/notifications/deliveries). Faltam:

- `senders.email_domains` (com DKIM/SPF/DMARC + reputation)
- `senders.dedicated_ips` (warmup management)
- `senders.whatsapp_numbers` (espelho CONNECT)
- `senders.push_apps` (APNs/FCM/VAPID configs)
- `templates.email_templates` + `templates.sms_templates` + `templates.push_templates` (já existe básico, expandir colunas)
- `suppression.entries` (cross-canal com index crítico)
- `webhooks.endpoints` + `webhooks.deliveries` (já existe, refazer com FK)
- `providers.sms_provider_routes` (config Zenvia/TotalVoice routing)

## Critérios de aceite

- [ ] Migration `0002_expand_schema.py` cria 10+ tabelas com schemas
  apropriados (senders, suppression, webhooks, providers)
- [ ] Schemas separados criados: `senders`, `suppression`, `webhooks`,
  `providers`, `templates` (search_path inclui todos)
- [ ] Indexes críticos: `suppression.entries (organization_id,
  identifier_type, identifier_value)` para latência <2ms check
- [ ] Foreign keys com `ON DELETE CASCADE` apropriado
- [ ] CHECK constraints para enums (status, kind, etc)
- [ ] `down_revision = "0001_initial"` correto
- [ ] Migration reversível (downgrade testado)
- [ ] SQLAlchemy models em `db/models.py` espelham schema
- [ ] Tests fixture com 1 row por tabela passing

## Referências

- [BEACON.md §2.7 schema completo](../../BEACON.md)
- [ADR 0002 — Data model Postgres + ClickHouse split](../../adr/0002-data-model-postgres-clickhouse-split.md)
- [docs/api/API_SPEC.md](../../api/API_SPEC.md)
- migration existente `migrations/versions/0001_initial.py`

## Notas implementação

- Schema-aware Alembic (search_path inclui múltiplos schemas)
- `gen_random_uuid()` (pgcrypto extension) — adicionar extension em migration
- Vault paths armazenam apenas `path` string; valores reais sempre via ESO
- Webhook signing_secret_vault_path coluna texto; não armazenar secret raw

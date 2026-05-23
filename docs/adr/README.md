# Architecture Decision Records (ADRs) — BEACON

ADRs capturam decisões arquiteturais não-triviais do BEACON (Notification
Platform Multi-Canal BR). Estrutura mínima: Status, Contexto, Decisão,
Consequências, Alternativas consideradas, Referências.

## Índice

| # | Título | Status |
|---|---|---|
| [0000](0000-template.md) | Template MADR (copiar como base) | Template |
| [0001](0001-backend-language-fastapi-python.md) | Backend BEACON em FastAPI + Python 3.13 | Aceita |
| [0002](0002-data-model-postgres-clickhouse-split.md) | Data model split: Postgres 17 + ClickHouse 24 | Aceita |
| [0003](0003-auth-authentik-oidc-api-tokens.md) | Auth: Authentik OIDC (UI) + API tokens (SDK/REST) | Aceita |
| [0004](0004-multi-tenancy-rls-postgres.md) | Multi-tenancy 4 camadas (RLS + Postal vhosts + Kafka ACL + ClickHouse) | Aceita |
| [0005](0005-cross-product-integrations.md) | Integrações cross-product (FOUNDRY+HOST+AUDIT-TRAIL+GUARDIAN+CONNECT) | Aceita |

## Numeração

Monotonicamente crescente; não reusar slots.

## Relação com cluster ADRs

ADRs cluster (`rewire_cluster/docs/adr/`) prevalecem em decisões
cross-product. ADRs deste repo cobrem decisões BEACON-specific.

## Decisões fechadas em BEACON.md §2.0

BEACON.md raiz tem 25 decisões fechadas durante design (decisão 1-25).
As ADRs aqui formalizam as **decisões estruturais mais relevantes** para
quem vai implementar; decisões de stack OSS (decisão 1 Postal, decisão 2
SES, etc) são referenciadas inline nas ADRs sem ADR dedicado.

Quando uma nova decisão estrutural surgir durante implementação que não
esteja em BEACON.md §2.0, criar ADR aqui.

# BCN-024 — Endpoint `POST /v1/messages/email` body real (substituir stub V0.2)

**Owner**: backend
**Estimativa**: L (2-3d)
**Pré-requisitos**: [[BCN-010]] schema expand, [[BCN-011]] RLS,
[[BCN-013]] auth middleware, [[BCN-020]] Postal infra,
[[BCN-021]] Postal client, [[BCN-028]] template rendering

## Definição

Substituir stub atual de `POST /v1/messages/email` (retorna
`{"status":"not_implemented","todo":"V0.2"}`) por implementação real
end-to-end:

1. Validar payload (FROM domain pertence ao tenant, sender verified)
2. Verificar quota mensal (`organizations.monthly_quota_email`)
3. Verificar suppression list (`suppression.entries` lookup <2ms)
4. Verificar frequency cap (Redis sliding window)
5. Anti-spam ML check (V0.4+ stub OK por enquanto)
6. Render template (MJML compile + Handlebars-like vars)
7. Compute BLAKE3 audit chain hash (content + recipient + timestamp +
   consent_basis)
8. CITADEL chain anchor POST `/chain/append` (async fire-and-forget)
9. Enqueue Kafka topic `beacon.send.email.<tier>`
10. Return `202 Accepted` com `message_id` (ULID) + `chain_hash`
    provisional

Worker `email_sender` (separate ticket [[BCN-023]]) consome Kafka e
faz fan-out para Postal/SES.

## Critérios de aceite

- [ ] Endpoint implementado com Pydantic schema completo (BEACON.md
  §2.10 OpenAPI)
- [ ] Validações 1-6 funcionais (suppression é hard requirement)
- [ ] BLAKE3 hash determinístico (mesmo input → mesmo hash)
- [ ] Idempotency-Key header respeitado (24h TTL Redis)
- [ ] Kafka producer com retry exponencial; falha = 503 ao cliente
- [ ] Audit emit `message.email.queued` per request
- [ ] Rate limit per-tenant via Redis sliding window
- [ ] Tests integration: mock Postal + verify Kafka publish + verify
  suppression block
- [ ] Tests RLS: tenant X não pode enviar usando domain de tenant Y
- [ ] Tests load: 1000 RPS sustained sem 5xx
- [ ] SLA p95 <100ms enqueue (excluindo Kafka latency)

## Referências

- [BEACON.md §2.10 endpoint OpenAPI](../../BEACON.md)
- [ADR 0002 — Data model Postgres + ClickHouse + Kafka split](../../adr/0002-data-model-postgres-clickhouse-split.md)
- [ADR 0004 — Multi-tenancy 4 camadas](../../adr/0004-multi-tenancy-rls-postgres.md)
- [docs/api/API_SPEC.md §2 Messages hot path](../../api/API_SPEC.md)
- [[BCN-023]] worker Kafka consumer
- [[BCN-035]] suppression service
- [[BCN-120]] BLAKE3 chain hash CITADEL

## Notas implementação

- ULID para message_id (sortable cross-time, ordenado em Kafka partition)
- Suppression check deve usar prepared statement + index dedicado
- Quota check: Redis counter + Postgres sync hourly (eventually consistent
  OK para quota)
- CITADEL anchor async; falha não bloqueia envio (audit eventually
  consistent)
- Kafka topic naming alinhado [[ADR-0002]]: `beacon.send.email.<tier>`
- Lawful basis obrigatório (LGPD): consent/contract/legal/legitimate

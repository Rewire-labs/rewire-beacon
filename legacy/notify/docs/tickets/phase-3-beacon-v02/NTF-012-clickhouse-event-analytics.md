# NTF-012 — ClickHouse 24.x event analytics

- **Owner**: @alessandro
- **Estimativa**: L
- **Pre-reqs**: ClickHouse UP
- **Status**: [ ] open (V0.2)

## Definicao

Para BEACON V0.2 multi-canal, precisamos analytics: delivery rate per
canal, bounce rate, click-through, opt-out rate, latencia por destino.

ClickHouse 24.x columnar com `MergeTree` engine + ingest async via
Kafka consumer.

## Aceite

- [ ] Schema `notify_events` (kind, channel, recipient_hash,
  delivery_status, bounce_reason, click_count, ts).
- [ ] Kafka consumer `notify.events.delivery` topic.
- [ ] Grafana dashboards.
- [ ] LGPD: recipient hashed (SHA-256 salted).

## Refs

- [ADR 0009](../../adr/0009-beacon-v0-2-multi-canal-roadmap.md)

## Notas

Cross-product: PULSE-CLOUD pode consumer dashboards.

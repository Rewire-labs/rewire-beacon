# NTF-004 — Kafka consumer `cluster.events.global`

- **Owner**: @alessandro
- **Estimativa**: M
- **Pre-reqs**: Redpanda UP
- **Status**: [~] partial (`kafka_consumer.py` scaffolded, integration test pending)

## Definicao

Background consumer (`aiokafka`) subscribe topic `cluster.events.global`,
deserializa msg como JSON → `AlertEvent`, fan-out via `Dispatcher`.

## Aceite

- [ ] Consumer group `rewire-notify-v1`.
- [ ] Manual commit apos dispatch sucesso.
- [ ] Retry com backoff para falhas dispatch.
- [ ] Pytest com Kafka container (testcontainers ou fake broker).
- [ ] Health check ready depende consumer healthy.

## Refs

- [ADR 0003](../../adr/0003-redpanda-kafka-consumer.md)
- `src/rewire_notify/kafka_consumer.py`

## Notas

Single-pod consumer V0.1 (consumer group oferece HA quando multi-pod).

# ADR 0003 — Redpanda Kafka consumer `cluster.events.global`

- **Status**: Accepted
- **Data**: 2026-05-18
- **Decisores**: Alessandro Queiroz
- **Consulta tecnica**: cluster ADR Redpanda + Kafka API

## Contexto

Producers do cluster (`foundry`, `vector`, `metering`, `audit-trail`,
etc) emitem eventos relevantes em topics Redpanda. Sem consumer
centralizado, notificacao depende de cada producer chamar `/events`
HTTP — coupling ruim.

## Decisao

Implementar **Kafka consumer** em background task (`kafka_consumer.py`)
que consome `cluster.events.global` topic (Redpanda compativel Kafka
API). Cada msg deserializa para `AlertEvent` e fan-out via
`Dispatcher`.

Configuravel:
- `kafka_brokers=redpanda.kafka:9092`
- `kafka_topic_events=cluster.events.global`
- `kafka_consumer_group=rewire-notify-v1`
- `enable_kafka_consumer=true`

## Alternativas consideradas

1. **Polling Loki/Prometheus**
   - Pros: dados ja agregados.
   - Contras: latencia alta; nao captura eventos non-metric.
   - Descartada.

2. **HTTP POST direto pelos producers**
   - Pros: simples.
   - Contras: coupling N-para-1; producers tem que conhecer notify
     URL; sem retry/durable.
   - Descartada: webhook fan-out fragil.

3. **NATS/JetStream**
   - Pros: lightweight.
   - Contras: cluster ja escolheu Redpanda (cluster ADR 0007).
   - Descartada: alinhamento.

## Consequencias

- **Positivas**: producer apenas publica em topic; consumer
  desacoplado; multiple consumers possivel (audit, ML training);
  replay via Kafka offset.
- **Negativas**: consumer eh stateful (consumer group); restart
  precisa cuidado em offset.
- **Neutras**: producer side ainda tem `/events` POST endpoint
  fallback (producers sem Redpanda access).

## Proximas acoes

- Ticket [[NTF-004]] — implementar consumer Kafka.
- Ticket [[NTF-005]] — eventos producer canonicos por cross-product.

## Referencias

- `src/rewire_notify/kafka_consumer.py`
- cluster ADR Redpanda

## Historico de revisoes

| Data | Autor | Mudanca |
|---|---|---|
| 2026-05-23 | audit-agent | criacao retroativa |

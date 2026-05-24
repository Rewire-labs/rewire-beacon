# BCN-V2006 — Strimzi Kafka topics provisioning (BCN-092)

**Owner**: infra
**Estimativa**: S (3-5d)
**Pré-requisitos**: Strimzi operator cluster-wide
**Detected by**: audit pass-2 (2026-05-24, ainda em backlog BCN-092)

## Contexto

BCN-092 marked [ ]: Kafka topics `beacon.events.<channel>` via Strimzi CRDs.
Workers (BCN-023/052/062/081) consomem desses topics — sem provisioning
fica em fallback in-memory ou crash.

## Definição

1. `cluster/kafka-topics.yaml` com Strimzi `KafkaTopic` CRDs:
   - `beacon.events.email` (24 partições, retention 30d)
   - `beacon.events.sms` (12 partições, retention 30d)
   - `beacon.events.push` (12 partições, retention 30d)
   - `beacon.events.whatsapp` (12 partições, retention 30d)
   - `beacon.commands.send_email` (24 partições, retention 7d)
   - `beacon.commands.send_sms` (12 partições)
   - `beacon.commands.send_push` (12 partições)
   - `beacon.commands.send_whatsapp` (12 partições)
   - `beacon.audit.chain` (6 partições, retention 7y compact)
2. KafkaUser CRDs com ACLs por worker (least privilege).
3. NetworkPolicy: BEACON workers → Strimzi brokers permit.

## Critérios de aceite

- [ ] 9 topics criados (`kubectl get kt -n beacon`)
- [ ] Workers consumindo successfully (lag <1s p95)
- [ ] ACLs negam workers cross-channel (email worker não consome sms topic)

## Referências

- BCN-092 (original)
- BCN-023/052/062/081 (worker dependents)

# BCN-V2005 — ClickHouse cluster deploy 3 nodes Helm (BCN-090)

**Owner**: infra + backend
**Estimativa**: M (1 sprint)
**Pré-requisitos**: Strimzi Kafka (BCN-V2006)
**Detected by**: audit pass-2 (2026-05-24, ainda em backlog BCN-090)

## Contexto

BCN-090 marked [ ]: ClickHouse cluster provisioning Helm chart 3 nodes.
Schema (BCN-091) + Kafka engine (BCN-093) + queries (BCN-094/095/096) já
existem mas SEM cluster as queries falham.

## Definição

1. Helm chart `clickhouse-operator` ou Bitnami/Altinity 3 nodes.
2. ZooKeeper cluster 3 nodes (replication coordination).
3. Database `beacon_events` + tables conforme `clickhouse_schema.sql`.
4. Persistent volume CSI Ceph RBD per node.
5. Backup CronJob daily → MinIO `beacon-clickhouse-backup`.
6. ServiceMonitor expondo `clickhouse_*` metrics.
7. Retention policy 1y default, 7y para Enterprise tier.

## Critérios de aceite

- [ ] 3 nodes ready (`kubectl get chi -n beacon`)
- [ ] Replication funcional (insert em node1 visible em node2/3 <1s)
- [ ] Backup CronJob success daily
- [ ] Endpoint `/v1/analytics/messages` retorna dados reais

## Referências

- BCN-090 (original)
- BCN-091/093/094/095/096 (dependent tickets)

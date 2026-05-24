# BCN-101 — RabbitMQ producer/consumer topics canonical

## Fase
phase-6-inter-agent-comm

## Owner sugerido
backend

## Estimativa
M (4-6h)

## Pre-requisitos
- [[BCN-100]]
- RabbitMQ cluster acessivel (reuso [[CNT-042]] topology)
- Vault path `secret/rewire/beacon-ai/rmq` credenciais

## Definicao

Producer:

- Emitir eventos relevantes do service em routing key
  `agent.beacon-ai.<dst>.<event>` (envelope canonical
  [[INTER_AGENT_COMM_SPEC]] secao 2.3)
- Eventos minimos: state-change relevante + completion long-running

Consumer:

- Subscrever `agent.metering.*.budget_exhausted` -> degrade
- Subscrever `agent.citadel.*.chain_appended` -> cross-link audit
- Subscrever `agent.tenant.*.policy_changed` -> reload policy
- Subscrever `agent.*.<agent_id>.*` -> reagir a eventos direcionados

### Steps

1. Criar `agent_bus_rmq.py` (producer + consumer aio-pika async)
2. Wire producer em pontos de state-change
3. Wire consumer em startup lifespan
4. NetworkPolicy egress permitir RMQ
5. Helm values: env `RMQ_URL` via ExternalSecret

## Criterios de aceite

- [ ] Producer emite eventos com envelope canonical
- [ ] Consumer processa pelo menos 3 routing keys
- [ ] DLQ wired (reuso [[CNT-042]])
- [ ] Smoke test E2E

## Referencias

- [[INTER_AGENT_COMM_SPEC]] secao 2
- [[CNT-042]] DLQ pattern reuso

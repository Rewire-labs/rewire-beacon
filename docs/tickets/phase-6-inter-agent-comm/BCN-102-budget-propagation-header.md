# BCN-102 — Budget propagation via X-Rewire-Tenant-Budget header

## Fase
phase-6-inter-agent-comm

## Owner sugerido
backend

## Estimativa
S (2-3h)

## Pre-requisitos
- [[BCN-100]]
- rewire-tenant-metering API `/budget/<tenant>/remaining` disponivel

## Definicao

Em `/agent/v1/invoke`:

1. Ler `X-Rewire-Tenant-Budget` header (formato `usd=0.42;ttl_s=60`)
2. Se ausente, query rewire-tenant-metering
3. Se < `metadata.max_cost_usd` da request, retornar 402 com code
   `BUDGET_EXCEEDED` SEM consumir LLM
4. Apos LLM call interna, decrementar budget local e propagar header em
   sub-chamadas (`AgentBusClient.invoke` passa header atualizado)
5. Emitir `agent.beacon-ai.metering.budget_consumed` evento RMQ pra
   reconciliacao

## Criterios de aceite

- [ ] Header lido e respeitado em `/invoke`
- [ ] 402 retornado se budget excede
- [ ] Sub-calls recebem header com saldo atualizado
- [ ] Evento RMQ emitido pos-call

## Referencias

- [[INTER_AGENT_COMM_SPEC]] secao 7

# BCN-103 — OpenTelemetry span cross-agent

## Fase
phase-6-inter-agent-comm

## Owner sugerido
backend

## Estimativa
S (2-3h)

## Pre-requisitos
- [[BCN-100]], [[BCN-101]]
- OTel collector cluster acessivel

## Definicao

Instrumentar:

- Span `rewire.agent.call` cliente sincrono
- Span `rewire.agent.serve` servidor recebendo
- Span `rewire.agent.publish` / `rewire.agent.consume` RMQ
- Attributes: `rewire.agent.src`, `rewire.agent.dst`,
  `rewire.tenant.id`, `rewire.capability`, `rewire.cost_usd`,
  `rewire.audit_chain_hash`
- Context propagation W3C `traceparent` + custom `X-Rewire-Trace-Id`

### Steps

1. Adicionar `opentelemetry-instrumentation-fastapi` + `httpx` + `aio-pika`
2. Exporter OTLP gRPC -> cluster collector
3. `AgentBusClient` injeta context headers
4. Helm values: `OTEL_EXPORTER_OTLP_ENDPOINT`

## Criterios de aceite

- [ ] Trace cross-agent visivel em Tempo (beacon-ai -> outro)
- [ ] Attributes populados
- [ ] Metricas `rewire_agent_call_total{src,dst,status}` em Prometheus

## Referencias

- [[INTER_AGENT_COMM_SPEC]] secao 5

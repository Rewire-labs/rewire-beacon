# BCN-100 — REST client cross-agent (retry + idempotency + audit)

## Fase
phase-6-inter-agent-comm

## Owner sugerido
backend

## Estimativa
M (4-6h)

## Pre-requisitos
- [[INTER_AGENT_COMM_SPEC]] V0 aprovado
- [[CROSS_AGENT_AUTH_ADR]] aprovado (JWT issuer ou shared-secret legacy)

## Definicao

Implementar `AgentBusClient` HTTP canonical pra chamar outros agents IA via
`/agent/v1/invoke`, com:

- Headers obrigatorios `X-Rewire-Agent-Src=beacon-ai`, `Dst`,
  `Trace-Id`, `Span-Id`, `Tenant-Id`, `Idempotency-Key` em POST
- Retry exponential backoff (200ms, 1s, 5s — max 3)
- Idempotency-Key UUIDv4 auto-gerado por call
- Audit chain ref propagation: ler `audit_chain_hash` da response e
  passar como `X-Rewire-Audit-Chain-Ref` na proxima call
- Auth header `Authorization: Bearer <jwt>` (refresh JWT via Authentik)
- Timeout default 30s (override por capability via Registry annotation)

### Steps

1. Criar `apps/control-plane/src/.../agent_bus_client.py` (path conforme repo)
2. Wire em rotas/agents que chamam capabilities externas
3. Emitir span OTel `rewire.agent.call` em cada invocacao
4. Testes unit: 200 OK, 429 + Retry-After, 401 sem retry, idempotency dedupe

## Criterios de aceite

- [ ] Cliente em codebase
- [ ] Codigo IA usa cliente (nao mais httpx direto)
- [ ] Span OTel cross-agent visivel em Tempo
- [ ] Test suite passa

## Referencias

- [[INTER_AGENT_COMM_SPEC]] secao 1
- [[CROSS_AGENT_AUTH_ADR]]

# NTF-AICX-01 — Integração Central AI Chat (NOTIFY)

**Owner**: backend (rewire-notify)
**Estimativa**: M (2-4 dias)
**Pré-requisitos**:
- [[CAPABILITY_REGISTRY_SPEC]] (`services/CAPABILITY_REGISTRY_SPEC.md`) — schema canonical
- [[INTER_AGENT_COMM_SPEC]] (`services/INTER_AGENT_COMM_SPEC.md`) — protocolo `/agent/v1/invoke`
- [[CROSS_AGENT_AUTH_ADR]] (`services/CROSS_AGENT_AUTH_ADR.md`) — JWT M2M `agents.rewire.svc`
- [[CENTRAL_AI_CHAT_SPEC]] (`services/CENTRAL_AI_CHAT_SPEC.md`) — escopo cliente do contract
- [[APP-ADR-0017]] (`services/rewire-app/docs/adr/0017-central-ai-chat-orchestrator.md`) — ADR canonical
- [[ADR-cluster-0107]] (`docs/adr/0107-central-ai-chat-orchestrator-canonical-v0.md`) — ADR cluster
- NTF-CAP-01 (já criado em `phase-9-capability-registry/`) — REST registry baseline

**Cross-cutting**: ticket replicado nos 34 serviços do ecossistema com este mesmo escopo (ID `AICX-01`).
**Phase**: `phase-99-ai-centric` (deliberadamente alta para não colidir com phases existentes).
**Detected by**: design Central AI Chat 2026-05-23.

## Contexto

A Rewire opera modelo **IA-centric**: cliente conversa com chat único
em `services/rewire-app/apps/chat-orchestrator/` (vide
[[APP-ADR-0017]]) que decompõe pedido NL PT-BR, descobre capabilities
via aggregator rewire-mcp ([[ADR-cluster-0106]]), **roteia para
master** (ASCEND ou FOUNDRY, [[MASTER_ORCHESTRATORS_SPEC]]) quando
intent envolve composição de software, ou **invoca capability atômica
direta** via `POST /agent/v1/invoke` ([[INTER_AGENT_COMM_SPEC]]).

Para participar do fluxo, **NOTIFY** precisa expor o endpoint
canonical `POST /agent/v1/invoke` aderente a [[INTER_AGENT_COMM_SPEC]]
mapeando para as capabilities já declaradas via NTF-CAP-01 em
`phase-9-capability-registry/`.

**Purpose do serviço (recap)**: Email/SMS/Push/Webhooks delivery centralizado + telegram bot ops.

**NOTIFY é serviço de PLATAFORMA sem IA própria** (vide [[AI_INVENTORY]] §Matrix `n/a`). Implementar endpoint `POST /agent/v1/invoke` ([[INTER_AGENT_COMM_SPEC]]) como thin wrapper sobre as operações REST existentes do serviço. Sem LLM no caminho — endpoint apenas valida o envelope canonical (headers + body), executa a operação determinística mapeada pelo capability_id, retorna resposta canonical com `cost_usd: 0` e `audit_chain_hash` propagado. Mantém serviço descobrível pelo chat-orchestrator sem inflar custo nem complexidade.

## Mudança

### 1. Endpoint canonical `POST /agent/v1/invoke`

Implementar handler aderente a [[INTER_AGENT_COMM_SPEC]] §1.3-§1.4.

**Request body**:

```json
{
  "capability": "rewire.notify.<capability_name>",
  "input": {},
  "metadata": {
    "deadline_ms": 30000,
    "max_cost_usd": 0.05,
    "reason": "agent_chain"
  }
}
```

**Request headers obrigatórios** ([[INTER_AGENT_COMM_SPEC]] §1.2):

- `Authorization: Bearer <JWT do agents.rewire.svc>` (validar via JWKS — [[CROSS_AGENT_AUTH_ADR]])
- `X-Rewire-Agent-Src` (esperado: `chat-orchestrator`)
- `X-Rewire-Agent-Dst` (esperado: nome canonical deste serviço)
- `X-Rewire-Trace-Id` (W3C `traceparent` também aceito)
- `X-Rewire-Span-Id` (OTel parent span)
- `X-Rewire-Tenant-Id` (`global` se ops-only)
- `X-Rewire-Idempotency-Key` (UUIDv4 — obrigatório em mutações, dedupe 24h)
- `X-Rewire-Audit-Chain-Ref` (anchor CITADEL chain origem)
- `X-Rewire-Tenant-Budget` (opcional — budget restante USD + TTL)

**Response body** ([[INTER_AGENT_COMM_SPEC]] §1.4):

```json
{
  "status": "ok | error | partial",
  "output": {},
  "cost_usd": 0.0,
  "latency_ms": 0,
  "audit_chain_hash": "blake3:...",
  "trace_id": "...",
  "error": null
}
```

**Behavior**:

1. Validar JWT `agents.rewire.svc` via JWKS cache 5min (FastAPI dep
   `verify_agent_jwt` shared em `rewire_shared/python/agent_auth.py`,
   a criar se não existir).
2. Validar `X-Rewire-Agent-Dst` corresponde a este serviço (rejeita
   se mismatch → 403).
3. Validar `capability` existe no registry deste serviço
   (`capabilities.yaml` lido em boot por CAP-01). Senão → 404.
4. Validar input contra `inputs_schema` declarado em `capabilities.yaml`.
5. Validar `metadata.deadline_ms` e `metadata.max_cost_usd` — abortar
   com `status=error, error.code=BUDGET_EXCEEDED` se previsão exceder.
6. Validar `X-Rewire-Idempotency-Key` dedupe (Redis SETNX TTL 24h).
   Replay retorna mesma response gravada.
7. Executar a capability mapeada (operação determinística + opcional
   LLM via NOVA Gateway).
8. Calcular `cost_usd` (LLM cost via NOVA headers `X-Usage-Cost-USD-Micro`
   se aplicável + custos de provisioning quando relevante).
9. Anchor response no CITADEL — propagar `audit_chain_hash` na
   response.
10. Emitir audit-trail event canonical `rewire.notify.<capability>.invoked`
    com payload `{tenant_id, actor_sub, input_hash, output_hash,
    tokens_used, latency_ms, hitl_required}` ([[CAPABILITY_REGISTRY_SPEC]]
    §Audit).
11. Emitir OTel span com atributos `rewire.agent.src`, `rewire.agent.dst`,
    `rewire.tenant.id`, `rewire.capability`, `rewire.cost_usd`.
12. Devolver response canonical.

### 2. Mapping capability_id → handler interno

Para **NOTIFY**, capabilities iniciais a mapear (alinhar com
`capabilities.yaml` que CAP-01 cria):

- `rewire.notify.send_email`
- `rewire.notify.send_push`
- `rewire.notify.create_template`

Cada `capability_id` mapeia para um handler interno que executa a
operação real. O endpoint `/agent/v1/invoke` é apenas o **wrapper
canonical** — handlers reusam código existente.

### 3. Retry, idempotency, rate-limit ([[INTER_AGENT_COMM_SPEC]] §1.5 + §4)

- Idempotency-Key obrigatório em mutação (dedupe 24h em Redis)
- Retry policy server-side: respeitar `metadata.deadline_ms`;
  abort cleanly com `status=error, error.code=TIMEOUT` se exceder
- Rate limit per-pair (src,dst): default 100 req/min (override via
  capability annotation `rate_limit.qpm`)
- 429 com header `Retry-After` obrigatório

### 4. Telemetria ([[INTER_AGENT_COMM_SPEC]] §5)

- OTel span obrigatório (export via cluster collector → Tempo)
- Métricas Prometheus: `rewire_agent_call_total{src,dst,status}`
  e `rewire_agent_cost_usd_sum{src,dst,tenant}`
- Audit-trail event canonical emitido

### 5. NetworkPolicy ingress

Atualizar NetworkPolicy do namespace deste serviço para aceitar
ingress do namespace `rewire-app` (onde mora chat-orchestrator) na
porta do `/agent/v1/invoke`.

### 6. Documentação local

- Adicionar seção em `docs/00-overview.md` (ou equivalente)
  descrevendo o endpoint `/agent/v1/invoke` e link para
  [[INTER_AGENT_COMM_SPEC]] + [[CENTRAL_AI_CHAT_SPEC]].
- Atualizar `docs/api/capabilities.md` (criado em CAP-01) listando
  o endpoint canonical de invoke + exemplos curl.
- Atualizar OpenAPI spec do serviço (rota nova listada).

## Critérios de aceite

- [ ] `POST /agent/v1/invoke` responde 200 (smoke test com JWT
      `agents.rewire.svc` válido + capability conhecida).
- [ ] JWT inválido → 401; capability desconhecida → 404; `Agent-Dst`
      mismatch → 403.
- [ ] Input schema validation funciona (capability registry valida
      via JSON Schema 2020-12).
- [ ] Idempotency replay: 2 calls com mesma `X-Rewire-Idempotency-Key`
      retornam mesma response (segundo é cache hit).
- [ ] Budget enforcement: `max_cost_usd=0.0001` aborta com
      `error.code=BUDGET_EXCEEDED`.
- [ ] Audit-trail event `rewire.notify.<capability>.invoked`
      emitido (verificável via AUDIT-TRAIL query).
- [ ] CITADEL anchor propagado: `X-Rewire-Audit-Chain-Ref` in →
      `audit_chain_hash` out (chain hash distinto, anchored).
- [ ] OTel span exportado para Tempo com atributos canonical.
- [ ] Métrica `rewire_agent_call_total` incrementa.
- [ ] NetworkPolicy aceita ingress de `rewire-app` namespace.
- [ ] OpenAPI atualizado + `docs/api/capabilities.md` enriquecido.
- [ ] Capability registry servido por CAP-01 inclui `agent_endpoint:
      /agent/v1/invoke` no payload de cada capability.

## Out-of-scope

- Implementação do chat-orchestrator que consome este endpoint —
  coberto em `APP-AICX-02` (skeleton) e `APP-AICX-03+` (features).
- Schema JSON canonical do envelope agent-invoke — coberto em
  ticket `rewire_shared` follow-up (publicar `agent_invoke.json`
  em `rewire_shared/python/schemas/`).
- Atualização do `MAPA_REWIRE.md` linha 25 (ADVISOR re-hospedagem)
  — coberto em ticket rewire_cluster root.
- Implementação de runtime IA novo onde `ai_status=planned` — coberto
  por `AI_INVENTORY` §Gap action plan + ADR per-service correspondente.

## Referências

- [[CENTRAL_AI_CHAT_SPEC]] — `services/CENTRAL_AI_CHAT_SPEC.md`
- [[CAPABILITY_REGISTRY_SPEC]] — `services/CAPABILITY_REGISTRY_SPEC.md`
- [[INTER_AGENT_COMM_SPEC]] — `services/INTER_AGENT_COMM_SPEC.md`
- [[CROSS_AGENT_AUTH_ADR]] — `services/CROSS_AGENT_AUTH_ADR.md`
- [[MASTER_ORCHESTRATORS_SPEC]] — `services/MASTER_ORCHESTRATORS_SPEC.md`
- [[AI_INVENTORY]] — `services/AI_INVENTORY.md`
- [[APP-ADR-0017]] — `services/rewire-app/docs/adr/0017-central-ai-chat-orchestrator.md`
- [[ADR-cluster-0106]] — `docs/adr/0106-capability-registry-mcp-canonical-v0.md`
- [[ADR-cluster-0107]] — `docs/adr/0107-central-ai-chat-orchestrator-canonical-v0.md`
- [[ADR-0037-foundry]] — V2 deepagents canonical
- [[ADR-0038-foundry]] — NOVA Gateway canonical
- NTF-CAP-01 (já criado) — REST registry baseline expondo `capabilities.yaml`

## Notas

- Não exige refactor de qualquer feature atual do **NOTIFY**.
- Implementação roda em paralelo com qualquer outro work do squad
  — endpoint novo, não toca código existente.
- O contract canonical é deliberadamente AGNÓSTICO de IA — serviços
  sem LLM (`ai_status=n/a`) também implementam (thin wrapper sobre
  REST existente). Isso garante que o chat-orchestrator possa
  invocar qualquer serviço uniformemente.
- Para serviços que JÁ têm `/agent/v1/invoke` parcial (caso raro,
  vide [[INTER_AGENT_COMM_SPEC]] §3 cross-refs), apenas alinhar com
  contract canonical — não recriar.

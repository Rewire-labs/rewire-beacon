# BCN-V2008 — Idempotency Redis-backed (substituir in-memory single-replica)

**Owner**: backend BEACON
**Estimativa**: S (3-5d)
**Pré-requisitos**: Redis cluster-wide HA
**Detected by**: audit pass-2 (2026-05-24)

## Contexto

`agents/agent_invoke_router.py:48` declara `_INMEM_IDEMPOTENCY: dict[str, dict[str, Any]] = {}`
com FIFO eviction. Comentário: "Production wires this to Redis via the
existing `beacon.middleware.IdempotencyMiddleware` Redis client". HPA
em prod terá ≥3 réplicas → dedup quebrado entre pods.

Curiosamente, BCN-015 já implementou `IdempotencyMiddleware` Redis mas
o agent router não consome essa dependência — gap de unificação.

## Definição

1. Refactor `agent_invoke_router.py` para receber `IdempotencyStore` por DI.
2. Wire `beacon.middleware.IdempotencyMiddleware.redis_client` em `app.py`.
3. Substituir `_get_cached_response/_set_cached_response/_clear` por store.
4. TTL 24h configurável via `BEACON_IDEMPOTENCY_TTL_SECONDS`.

## Critérios de aceite

- [ ] Multi-pod e2e test: 2 réplicas com mesmo idempotency-key → mesma response
- [ ] Metric `beacon_agent_idempotency_hits_total{src=...}`
- [ ] Graceful degradation se Redis indisponível

## Referências

- `apps/control-plane/src/beacon/agents/agent_invoke_router.py:48-134`
- BCN-015 IdempotencyMiddleware existente

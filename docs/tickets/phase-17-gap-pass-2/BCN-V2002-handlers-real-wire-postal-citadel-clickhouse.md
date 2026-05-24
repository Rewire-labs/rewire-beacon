# BCN-V2002 — Capability handlers real wire (Postal/CITADEL chain/ClickHouse)

**Owner**: backend BEACON
**Estimativa**: M (1 sprint)
**Pré-requisitos**: BCN-024/BCN-052/BCN-121 (services existentes)
**Detected by**: audit pass-2 (2026-05-24)

## Contexto

`agents/handlers.py` 6 capability handlers usam:
- `_synth_chain_hash()` (SHA-256 placeholder) ao invés do CITADEL chain real
- Comentários explícitos "production delegates to ..." mas wire NÃO foi feito
- `list_messages` retorna `count: 0` com `v0_stub: True`
- `check_suppression` retorna `false` heuristicamente (string "blocked")

## Definição

1. `send_email` — chamar `beacon.services.messaging.enqueue_email(...)` real → Kafka topic → email_sender worker → Postal API. Returnar `message_id` do DB.
2. `send_sms` — chamar `services.messaging.enqueue_sms(...)` → Zenvia BSP routing real.
3. `send_whatsapp` — chamar `services.messaging.enqueue_whatsapp(...)` → CONNECT BSP real.
4. `check_suppression` — chamar `services.suppression.check_cross_channel(tenant_id, type, value)` → Redis hot path <2ms.
5. `add_suppression` — INSERT INTO `beacon.suppression` + cross-channel propagation.
6. `list_messages` — SELECT FROM ClickHouse `beacon_events.messages_view` per tenant LIMIT N.
7. CITADEL chain hash real — substituir `_synth_chain_hash` por `citadel_chain.client.append_audit_event(...)` retornando `blake3:<real>` hash.

## Critérios de aceite

- [ ] Handler smoke test contra Postal/ClickHouse/CITADEL no cluster-dev
- [ ] `v0_stub: True` flag removida quando wire real
- [ ] Métrica `beacon_handler_real_calls_total{cap=...,status=...}`
- [ ] Audit chain entry visible em CITADEL após cada send

## Referências

- `apps/control-plane/src/beacon/agents/handlers.py` 6 handlers
- BCN-024 send_email path
- BCN-121 CITADEL anchor

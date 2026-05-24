# NTF-003 — `/alerts/telegram` HMAC + parser

- **Owner**: @alessandro
- **Estimativa**: M
- **Pre-reqs**: [[NTF-001]] [[NTF-002]]
- **Status**: [x] done

## Definicao

`POST /alerts/telegram` recebe Alertmanager webhook. HMAC opt-in via
`X-Rewire-Signature: sha256=<hex>`. Parser
`alertmanager_payload_to_events` deserializa para lista de `AlertEvent`,
fan-out via `dispatcher.dispatch_many`.

## Aceite

- [x] HMAC verify (empty secret = bypass dev).
- [x] Parser cobre alertname → EventKind mapping (crashloop, vault.sealed,
  smoke, cost, hardcap).
- [x] Severity inferida de `priority` (P0=critical, P1=warn) ou
  `severity` label.
- [x] Pytest cobertura.

## Refs

- [ADR 0004](../../adr/0004-hmac-alertmanager-opt-in.md)
- `src/rewire_notify/api.py`
- `src/rewire_notify/dispatcher.py`

## Notas

Alertname fallback eh `product.crashloop` (mais generico).

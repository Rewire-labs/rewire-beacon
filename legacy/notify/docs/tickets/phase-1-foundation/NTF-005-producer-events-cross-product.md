# NTF-005 — Producer events canonicos cross-product

- **Owner**: @alessandro + cross-product owners
- **Estimativa**: L
- **Pre-reqs**: [[NTF-004]]
- **Status**: [ ] open

## Definicao

Cada produto cross-cutting publica eventos canonicos no
`cluster.events.global` quando ativado:

- `tenant.onboarded` — rewire-admin
- `asaas.payment_received` — billing-client
- `product.crashloop` — Alertmanager (synthetic via /alerts/telegram)
- `vault.sealed` — Alertmanager
- `breach.detected` — citadel/guardian
- `tenant.hard_cap_exceeded` — vector/metering
- `lgpd.dsar.requested` — auth/admin
- `foundry.pr.merged` — foundry
- `daily.summary` — internal scheduler
- `smoke.test.failed` — CI (Gitea Actions)
- `cost.anomaly` — metering
- `pricing.change.applied` — admin

## Aceite

- [ ] SDK helper `rewire_shared.notify.publish(kind, severity, payload)`
  Python + Go.
- [ ] Doc per produto onde publicar.
- [ ] Integration tests cross-product.

## Refs

- [ADR 0002](../../adr/0002-12-event-kinds-canonical.md)
- [ADR 0003](../../adr/0003-redpanda-kafka-consumer.md)

## Notas

PR cross-repo para cada produto adicionar publish em momentos
relevantes.

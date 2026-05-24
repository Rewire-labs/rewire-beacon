# ADR 0010 — Cross-product compatibility: rewire-notify como predecessor BEACON

**Status**: Accepted
**Data**: 2026-05-23

## Contexto

`rewire-notify` é BEACON V0.1 internal core (Telegram dispatcher + Alertmanager
intake). `rewire-beacon` é V0.2+ multi-canal commercial. Matrix dimensão
8 trata notification universal.

## Decisão

rewire-notify e BEACON convergem:

1. rewire-notify continua servindo internal cluster (Telegram bot
   `@RewireLabsBot` + Alertmanager webhook + Kafka cluster.events.global).
2. BEACON V0.2+ multi-canal serve clientes externos.
3. Migration path: producers atuais (Alertmanager + Redpanda + APScheduler
   digest) reassinam BEACON SDK quando V0.2 GA.

## Consequências

- Sem disruption cluster interno.
- Migration controlada para BEACON V0.2.

## Cross-references

- Matrix dimensão 8
- Ticket: `docs/tickets/phase-1-cross-product-compat/xpc-notify-001-migrate-to-beacon.md`

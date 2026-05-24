# NTF-015 — Zenvia SMS channel (BR)

- **Owner**: @alessandro
- **Estimativa**: L
- **Pre-reqs**: [[NTF-010]] (API unificada), contrato Zenvia/TotalVoice
- **Status**: [ ] open (V0.2)

## Definicao

Canal SMS via Zenvia (BR carrier) ou TotalVoice. API HTTP.
Pricing varia ~R$ 0.08-0.15/SMS. Receiver pode reply STOP para
opt-out (callback via webhook).

## Aceite

- [ ] SmsAdapter implements `Adapter` interface.
- [ ] Templates curtos (160 chars).
- [ ] STOP reply webhook handler.
- [ ] ClickHouse delivery tracking.
- [ ] Pytest mock httpx.

## Refs

- [ADR 0009](../../adr/0009-beacon-v0-2-multi-canal-roadmap.md)
- [[NTF-013]] opt-out management

## Notas

Cost-sensitive: usar SMS so para `critical` events ou auth 2FA codes.

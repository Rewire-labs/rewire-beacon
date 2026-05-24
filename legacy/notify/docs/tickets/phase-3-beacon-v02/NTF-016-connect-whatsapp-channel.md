# NTF-016 — CONNECT WhatsApp channel (cross-product)

- **Owner**: @alessandro + CONNECT team (future Rewire product)
- **Estimativa**: XL
- **Pre-reqs**: CONNECT API UP (WhatsApp Business — produto futuro Rewire)
- **Status**: [ ] open (V0.2)

## Definicao

Canal WhatsApp via CONNECT (camada Rewire para WhatsApp Business API).
Suporta media (image, audio, video), interactive (buttons, lists),
templates aprovados Meta.

## Aceite

- [ ] WhatsAppAdapter implements `Adapter` interface.
- [ ] Template registry Meta-approved.
- [ ] Webhook delivery receipts.
- [ ] BLOQUEAR reply opt-out handler.
- [ ] Pytest com mock CONNECT API.

## Refs

- [ADR 0009](../../adr/0009-beacon-v0-2-multi-canal-roadmap.md)
- CONNECT spec (rewire_cluster futuros_produtos)

## Notas

CONNECT eh produto cross-product — depende roadmap separate.

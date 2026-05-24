# NTF-019 — Lago billing integration (per-notification metering)

- **Owner**: @alessandro
- **Estimativa**: M
- **Pre-reqs**: [[NTF-010]] [[NTF-015]] [[NTF-016]], Lago UP
- **Status**: [ ] open (V0.2)

## Definicao

BEACON V0.2 comercial: bill per notification sent (Pro+ tiers).
Lago billable_metric `notification_sent` per canal.

Pricing:
- Email: R$ 0.002/msg (Postal cost + margin)
- SMS: R$ 0.12/msg
- WA: R$ 0.05/msg
- Push: R$ 0.0005/msg
- Telegram: R$ 0 (internal only)

## Aceite

- [ ] Activity `forward_notification_to_lago` post-send.
- [ ] Idempotency key `notify-<event_id>-<channel>`.
- [ ] Per-tenant subscription tier.
- [ ] Killswitch overage.

## Refs

- [ADR 0009](../../adr/0009-beacon-v0-2-multi-canal-roadmap.md)
- cluster ADR Lago

## Notas

BEACON V0.2 monetization model.

# NTF-013 — Authentik consent management opt-outs

- **Owner**: @alessandro
- **Estimativa**: L
- **Pre-reqs**: Authentik UP, AUDIT TRAIL UP
- **Status**: [ ] open (V0.2)

## Definicao

LGPD: cada destino (email, SMS, WA, push) precisa consent registrado.
Opt-out via:

- Email unsubscribe link.
- SMS reply STOP.
- WA reply BLOQUEAR.
- Push setting in app.

Consent + opt-out anchored AUDIT TRAIL (CITADEL chain).

## Aceite

- [ ] Tabela `notify_consents` (recipient, channel, granted_at,
  revoked_at, source).
- [ ] Webhook receivers per canal.
- [ ] Pre-send gate: bloqueia se sem consent ou opt-out ativo.
- [ ] AUDIT TRAIL anchor per consent change.

## Refs

- [ADR 0009](../../adr/0009-beacon-v0-2-multi-canal-roadmap.md)
- cluster ADR 0054 (audit-trail)

## Notas

Bacen 4.658 + LGPD compliance evidence.

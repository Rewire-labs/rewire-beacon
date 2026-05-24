# NTF-020 — AUDIT TRAIL anchor consents + opt-outs

- **Owner**: @alessandro + AUDIT TRAIL team
- **Estimativa**: M
- **Pre-reqs**: [[NTF-013]], AUDIT TRAIL UP
- **Status**: [ ] open

## Definicao

Cada consent ou opt-out (LGPD evidence) anchored em CITADEL chain via
AUDIT TRAIL produto. Schema:

```json
{
  "event_type": "notify.consent.granted",
  "recipient_hash": "sha256(...)",
  "channel": "email",
  "source": "signup_form|sms_reply|profile_settings",
  "ts_ms": ...
}
```

## Aceite

- [ ] Activity `anchor_notify_consent` BLAKE3 hash.
- [ ] Schema persisted em `notify_consents.anchor_hash`.
- [ ] LGPD DSAR export inclui anchors.

## Refs

- [[NTF-013]]
- cluster ADR 0054

## Notas

Bacen 4.658 evidence + LGPD audit chain.

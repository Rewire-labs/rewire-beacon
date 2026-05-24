# NTF-021 — LGPD DSAR data export flow

- **Owner**: @alessandro
- **Estimativa**: M
- **Pre-reqs**: [[NTF-012]] [[NTF-013]]
- **Status**: [ ] open

## Definicao

LGPD: titular pode solicitar export de dados pessoais. NOTIFY armazena:
- recipient (email/phone) — pseudonimizado para audit/analytics.
- consent history.
- delivery history (per event sent).

Endpoint `POST /admin/dsar/notify-export` retorna ZIP per titular.

## Aceite

- [ ] DSAR request validation.
- [ ] Export ZIP com:
  - consents_history.csv
  - notifications_received.csv
  - audit_chain_hashes.json
- [ ] BEACON notify on completion (recursion).
- [ ] Auto-delete request data after 6 meses.

## Refs

- [[NTF-013]] [[NTF-020]]
- cluster `lgpd_dsar.py`

## Notas

Coordenado com central LGPD DSAR cluster-wide.

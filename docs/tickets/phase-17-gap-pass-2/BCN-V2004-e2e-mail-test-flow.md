# BCN-V2004 — E2E mail test full flow (BCN-029)

**Owner**: qa
**Estimativa**: S (3-5d)
**Pré-requisitos**: BCN-V2003 (Postal cluster), BCN-V2002 (handlers real)
**Detected by**: audit pass-2 (2026-05-24, ainda em backlog BCN-029)

## Contexto

BCN-029 marked [ ]: "Tests E2E: criar org → adicionar domain → verify DNS
→ enviar email → callback bounce". Sem este teste, ciclo completo email
não tem prova de funcionar end-to-end.

## Definição

1. Pytest E2E `tests/e2e/test_email_full_flow.py`:
   - Setup: criar org via Authentik OIDC stub
   - Step 1: POST `/v1/domains` com `example-beacon-test.com`
   - Step 2: POST `/v1/domains/{id}/verify` mockando DNS resolution
   - Step 3: POST `/v1/messages/email` body real
   - Step 4: poll `/v1/messages/{id}/events` até `delivered` (timeout 60s)
   - Step 5: inject Postal bounce webhook payload
   - Step 6: verify suppression list contém recipient
2. CI nightly job (não bloqueia PR).
3. Cleanup teardown em finally.

## Critérios de aceite

- [ ] Test passes em CI cluster-dev (não-flaky 10 runs consecutivos)
- [ ] Coverage relatório inclui flow
- [ ] Document em `docs/runbooks/e2e-test-failure-debug.md`

## Referências

- BCN-029 (original ticket)
- BCN-V2003 cluster prerequisite

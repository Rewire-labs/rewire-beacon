# BCN-241 — UI wire BeaconApiKeys

**Owner**: frontend
**Estimativa**: S (2-4h)
**Pré-requisitos**: `apps/beacon-ui/src/lib/api.ts`, endpoint `/v1/api-tokens`

## Definição

Wire `BeaconApiKeys.tsx` para CRUD api tokens via hook.

Steps:
1. Hook `use-api-tokens.ts`
2. Endpoints conforme [[BCN-162]]
3. Fallback offline

## Critérios de aceite

- [ ] List + create token (reveal one-time)
- [ ] Revoke mutation
- [ ] Loading + error + fallback

## Referências
- Backend: [[BCN-162]]
- Page: `apps/beacon-ui/src/pages/beacon/BeaconApiKeys.tsx`

## Notas
Sprint UI wiring pós-auditoria 2026-05-23.

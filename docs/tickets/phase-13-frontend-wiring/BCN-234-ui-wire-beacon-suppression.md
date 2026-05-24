# BCN-234 — UI wire BeaconSuppression

**Owner**: frontend
**Estimativa**: S (2-4h)
**Pré-requisitos**: `apps/beacon-ui/src/lib/api.ts`, endpoint `/v1/suppression`

## Definição

Wire `BeaconSuppression.tsx` para list + add/remove via hook.

Steps:
1. Hook `use-suppression.ts`
2. Endpoints conforme [[BCN-155]]
3. Fallback offline

## Critérios de aceite

- [ ] List filterable
- [ ] Add/remove mutations
- [ ] Loading + error + fallback

## Referências
- Backend: [[BCN-155]]
- Page: `apps/beacon-ui/src/pages/beacon/BeaconSuppression.tsx`

## Notas
Sprint UI wiring pós-auditoria 2026-05-23.

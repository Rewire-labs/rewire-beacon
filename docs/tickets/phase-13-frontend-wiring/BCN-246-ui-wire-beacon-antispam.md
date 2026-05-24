# BCN-246 — UI wire BeaconAntispam

**Owner**: frontend
**Estimativa**: S (2-4h)
**Pré-requisitos**: `apps/beacon-ui/src/lib/api.ts`, ML score endpoint

## Definição

Wire `BeaconAntispam.tsx` para ML score per tenant + whitelist mgmt.

Steps:
1. Hook `use-antispam.ts`
2. Endpoints conforme [[BCN-167]] + [[BCN-110]]-[[BCN-114]]
3. Fallback offline

## Critérios de aceite

- [ ] Score timeline chart
- [ ] Whitelist CRUD (BCN-114)
- [ ] Pattern detection alerts list
- [ ] Loading + error + fallback

## Referências
- Backend: [[BCN-167]], [[BCN-110]]-[[BCN-114]]
- Page: `apps/beacon-ui/src/pages/beacon/BeaconAntispam.tsx`

## Notas
Sprint UI wiring pós-auditoria 2026-05-23.

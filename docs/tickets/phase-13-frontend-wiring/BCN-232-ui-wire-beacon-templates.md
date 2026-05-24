# BCN-232 — UI wire BeaconTemplates

**Owner**: frontend
**Estimativa**: S (2-4h)
**Pré-requisitos**: `apps/beacon-ui/src/lib/api.ts`, endpoints `/v1/templates/*`

## Definição

Wire `BeaconTemplates.tsx` para CRUD + preview render via hook.

Steps:
1. Hook `use-templates.ts`
2. Endpoints conforme [[BCN-153]]
3. Fallback offline

## Critérios de aceite

- [ ] CRUD via mutations
- [ ] Preview render MJML
- [ ] Loading + error + fallback

## Referências
- Backend: [[BCN-153]]
- Page: `apps/beacon-ui/src/pages/beacon/BeaconTemplates.tsx`

## Notas
Sprint UI wiring pós-auditoria 2026-05-23.

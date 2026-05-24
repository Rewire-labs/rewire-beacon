# BCN-248 — UI wire BeaconTeam

**Owner**: frontend
**Estimativa**: S (2-4h)
**Pré-requisitos**: `apps/beacon-ui/src/lib/api.ts`

## Definição

Wire `BeaconTeam.tsx` para members + RBAC + invites.

Steps:
1. Hook `use-team.ts`
2. Endpoints conforme [[BCN-168]]
3. Fallback offline

## Critérios de aceite

- [ ] Members list + role edit
- [ ] Invite mutation + email send
- [ ] Loading + error + fallback

## Referências
- Backend: [[BCN-168]]
- Page: `apps/beacon-ui/src/pages/beacon/BeaconTeam.tsx`

## Notas
Sprint UI wiring pós-auditoria 2026-05-23.

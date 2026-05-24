# BCN-247 — UI wire BeaconSettings

**Owner**: frontend
**Estimativa**: S (2-4h)
**Pré-requisitos**: `apps/beacon-ui/src/lib/api.ts`

## Definição

Wire `BeaconSettings.tsx` para tenant prefs + notification channels.

Steps:
1. Hook `use-settings.ts`
2. Endpoints conforme [[BCN-168]]
3. Fallback offline

## Critérios de aceite

- [ ] Prefs load + save
- [ ] Notification channels CRUD
- [ ] Loading + error + fallback

## Referências
- Backend: [[BCN-168]]
- Page: `apps/beacon-ui/src/pages/beacon/BeaconSettings.tsx`

## Notas
Sprint UI wiring pós-auditoria 2026-05-23.

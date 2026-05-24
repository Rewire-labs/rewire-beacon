# BCN-233 — UI wire BeaconJourneys

**Owner**: frontend
**Estimativa**: S (2-4h)
**Pré-requisitos**: `apps/beacon-ui/src/lib/api.ts`, endpoints `/v1/journeys/*`

## Definição

Wire `BeaconJourneys.tsx` para list + start/pause/resume via hook. Visual flow builder fica em ticket separado [[BCN-104]].

Steps:
1. Hook `use-journeys.ts`
2. Endpoints conforme [[BCN-154]]
3. Fallback offline

## Critérios de aceite

- [ ] List + state badges
- [ ] Mutations start/pause/resume
- [ ] Loading + error + fallback

## Referências
- Backend: [[BCN-154]]
- Page: `apps/beacon-ui/src/pages/beacon/BeaconJourneys.tsx`

## Notas
Sprint UI wiring pós-auditoria 2026-05-23.

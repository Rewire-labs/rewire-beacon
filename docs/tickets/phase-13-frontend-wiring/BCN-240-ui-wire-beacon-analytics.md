# BCN-240 — UI wire BeaconAnalytics

**Owner**: frontend
**Estimativa**: S (2-4h)
**Pré-requisitos**: `apps/beacon-ui/src/lib/api.ts`, endpoint `/v1/analytics/messages`

## Definição

Wire `BeaconAnalytics.tsx` para ClickHouse-backed metrics via hook (cache Redis 5min backend-side).

Steps:
1. Hook `use-analytics.ts` (staleTime conservador 60s)
2. Endpoints conforme [[BCN-161]]
3. Fallback offline

## Critérios de aceite

- [ ] Time-series chart real data
- [ ] Per-channel breakdown
- [ ] Loading + error + fallback

## Referências
- Backend: [[BCN-161]]
- Page: `apps/beacon-ui/src/pages/beacon/BeaconAnalytics.tsx`

## Notas
Sprint UI wiring pós-auditoria 2026-05-23.

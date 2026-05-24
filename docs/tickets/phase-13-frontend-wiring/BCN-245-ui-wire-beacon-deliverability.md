# BCN-245 — UI wire BeaconDeliverability

**Owner**: frontend
**Estimativa**: S (2-4h)
**Pré-requisitos**: `apps/beacon-ui/src/lib/api.ts`, Postal reputation API

## Definição

Wire `BeaconDeliverability.tsx` para Postal reputation + IP warmup status.

Steps:
1. Hook `use-deliverability.ts`
2. Endpoints conforme [[BCN-166]]
3. Fallback offline

## Critérios de aceite

- [ ] IP reputation score
- [ ] Bounce/complaint rate widgets
- [ ] Warmup progress per IP
- [ ] Loading + error + fallback

## Referências
- Backend: [[BCN-166]]
- Page: `apps/beacon-ui/src/pages/beacon/BeaconDeliverability.tsx`

## Notas
Sprint UI wiring pós-auditoria 2026-05-23.

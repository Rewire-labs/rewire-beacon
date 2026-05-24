# BCN-236 — UI wire BeaconSmsNumbers

**Owner**: frontend
**Estimativa**: S (2-4h)
**Pré-requisitos**: `apps/beacon-ui/src/lib/api.ts`, endpoint `/v1/sms-numbers`

## Definição

Wire `BeaconSmsNumbers.tsx` para CRUD + pricing display.

Steps:
1. Hook `use-sms-numbers.ts`
2. Endpoints conforme [[BCN-157]]
3. Fallback offline

## Critérios de aceite

- [ ] List + BSP routing display
- [ ] Pricing pass-through visível (BEACON.md §2.2.2)
- [ ] Loading + error + fallback

## Referências
- Backend: [[BCN-157]]
- Page: `apps/beacon-ui/src/pages/beacon/BeaconSmsNumbers.tsx`

## Notas
Sprint UI wiring pós-auditoria 2026-05-23.

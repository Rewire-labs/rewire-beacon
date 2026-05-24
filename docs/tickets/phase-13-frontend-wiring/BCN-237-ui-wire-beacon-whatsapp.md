# BCN-237 — UI wire BeaconWhatsapp

**Owner**: frontend
**Estimativa**: S (2-4h)
**Pré-requisitos**: `apps/beacon-ui/src/lib/api.ts`, endpoint `/v1/whatsapp`

## Definição

Wire `BeaconWhatsapp.tsx` para templates approved + quality rating display.

Steps:
1. Hook `use-whatsapp.ts`
2. Endpoints conforme [[BCN-158]]
3. Fallback offline
4. Quality rating display (BCN-084 separately)

## Critérios de aceite

- [ ] Templates list synced de CONNECT
- [ ] Approved/rejected badges
- [ ] Quality rating display
- [ ] Loading + error + fallback

## Referências
- Backend: [[BCN-158]]
- Page: `apps/beacon-ui/src/pages/beacon/BeaconWhatsapp.tsx`

## Notas
Sprint UI wiring pós-auditoria 2026-05-23.

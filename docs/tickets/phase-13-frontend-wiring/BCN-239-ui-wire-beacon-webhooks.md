# BCN-239 — UI wire BeaconWebhooks

**Owner**: frontend
**Estimativa**: S (2-4h)
**Pré-requisitos**: `apps/beacon-ui/src/lib/api.ts`, endpoint `/v1/webhooks`

## Definição

Wire `BeaconWebhooks.tsx` para CRUD + test delivery + HMAC config.

Steps:
1. Hook `use-webhooks.ts`
2. Endpoints conforme [[BCN-160]]
3. Fallback offline

## Critérios de aceite

- [ ] CRUD via mutations
- [ ] Test delivery trigger
- [ ] HMAC secret reveal/rotate
- [ ] Loading + error + fallback

## Referências
- Backend: [[BCN-160]]
- Page: `apps/beacon-ui/src/pages/beacon/BeaconWebhooks.tsx`

## Notas
Sprint UI wiring pós-auditoria 2026-05-23.

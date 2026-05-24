# BCN-238 — UI wire BeaconPushApps

**Owner**: frontend
**Estimativa**: S (2-4h)
**Pré-requisitos**: `apps/beacon-ui/src/lib/api.ts`, endpoint `/v1/push-apps`

## Definição

Wire `BeaconPushApps.tsx` para CRUD + cert upload via hook.

Steps:
1. Hook `use-push-apps.ts`
2. Endpoints conforme [[BCN-159]]
3. Fallback offline

## Critérios de aceite

- [ ] CRUD apps (iOS/Android/Web)
- [ ] Cert upload (APNs .p8, FCM .json)
- [ ] VAPID key reveal (web)
- [ ] Loading + error + fallback

## Referências
- Backend: [[BCN-159]]
- Page: `apps/beacon-ui/src/pages/beacon/BeaconPushApps.tsx`

## Notas
Sprint UI wiring pós-auditoria 2026-05-23.

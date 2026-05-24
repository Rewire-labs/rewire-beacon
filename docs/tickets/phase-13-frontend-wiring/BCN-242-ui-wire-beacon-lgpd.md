# BCN-242 — UI wire BeaconLgpd

**Owner**: frontend
**Estimativa**: S (2-4h)
**Pré-requisitos**: `apps/beacon-ui/src/lib/api.ts`, endpoint `/v1/audit/lgpd/dsar`

## Definição

Wire `BeaconLgpd.tsx` para DSAR submit + status + export download.

Steps:
1. Hook `use-lgpd.ts`
2. Endpoints conforme [[BCN-163]]
3. Fallback offline

## Critérios de aceite

- [ ] DSAR submit form
- [ ] Status countdown (LGPD 15d)
- [ ] Export download presigned URL
- [ ] Loading + error + fallback

## Referências
- Backend: [[BCN-163]]
- Page: `apps/beacon-ui/src/pages/beacon/BeaconLgpd.tsx`

## Notas
Sprint UI wiring pós-auditoria 2026-05-23.

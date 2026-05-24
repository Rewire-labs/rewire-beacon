# BCN-235 — UI wire BeaconDomains

**Owner**: frontend
**Estimativa**: S (2-4h)
**Pré-requisitos**: `apps/beacon-ui/src/lib/api.ts`, endpoints `/v1/domains`

## Definição

Wire `BeaconDomains.tsx` para CRUD + verify DNS via hook.

Steps:
1. Hook `use-domains.ts`
2. Endpoints conforme [[BCN-156]]
3. Fallback offline

## Critérios de aceite

- [ ] CRUD via mutations
- [ ] DNS records reveal (DKIM/SPF/DMARC)
- [ ] Verify button dispara backend
- [ ] Loading + error + fallback

## Referências
- Backend: [[BCN-156]]
- Page: `apps/beacon-ui/src/pages/beacon/BeaconDomains.tsx`

## Notas
Sprint UI wiring pós-auditoria 2026-05-23.

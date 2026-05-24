# BCN-243 — UI wire BeaconBilling

**Owner**: frontend
**Estimativa**: S (2-4h)
**Pré-requisitos**: `apps/beacon-ui/src/lib/api.ts`, endpoints `/v1/billing/*`

## Definição

Wire `BeaconBilling.tsx` para usage MTD + invoices via hook.

Steps:
1. Hook `use-billing.ts`
2. Endpoints conforme [[BCN-164]] + [[BCN-135]]
3. Fallback offline

## Critérios de aceite

- [ ] MTD usage breakdown (emails/sms/push/wa/ips)
- [ ] Invoices list + download
- [ ] Overage warning banner
- [ ] Loading + error + fallback

## Referências
- Backend: [[BCN-164]], [[BCN-135]]
- Page: `apps/beacon-ui/src/pages/beacon/BeaconBilling.tsx`

## Notas
Sprint UI wiring pós-auditoria 2026-05-23.

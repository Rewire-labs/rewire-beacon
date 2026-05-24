# BCN-231 — UI wire BeaconMessages

**Owner**: frontend
**Estimativa**: S (2-4h)
**Pré-requisitos**: `apps/beacon-ui/src/lib/api.ts`, endpoint `/v1/messages`

## Definição

Wire `apps/beacon-ui/src/pages/beacon/BeaconMessages.tsx` para list + filter via TanStack Query.

Steps:
1. Criar hook `apps/beacon-ui/src/lib/hooks/use-messages.ts`
2. Endpoint `GET /v1/messages?status=&channel=` (já em [[BCN-152]])
3. Remover mock + fallback banner

## Critérios de aceite

- [ ] List paginated via hook
- [ ] Filter status/channel funciona
- [ ] Loading + error + fallback offline

## Referências
- Backend: [[BCN-152]]
- Cliente: `apps/beacon-ui/src/lib/api.ts`
- Page: `apps/beacon-ui/src/pages/beacon/BeaconMessages.tsx`

## Notas
Sprint UI wiring pós-auditoria 2026-05-23.

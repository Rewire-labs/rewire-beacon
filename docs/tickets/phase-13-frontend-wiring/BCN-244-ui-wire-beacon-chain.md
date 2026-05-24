# BCN-244 — UI wire BeaconChain

**Owner**: frontend
**Estimativa**: S (2-4h)
**Pré-requisitos**: `apps/beacon-ui/src/lib/api.ts`, endpoint chain BLAKE3

## Definição

Wire `BeaconChain.tsx` para visualização audit chain BLAKE3 per message.

Steps:
1. Hook `use-chain.ts`
2. Endpoints conforme [[BCN-165]] + [[BCN-121]] CITADEL anchor
3. Fallback offline

## Critérios de aceite

- [ ] Chain entries list (hash + prev_hash + timestamp)
- [ ] Search by message_id
- [ ] Verify chain integrity badge
- [ ] Loading + error + fallback

## Referências
- Backend: [[BCN-165]], [[BCN-121]]
- Page: `apps/beacon-ui/src/pages/beacon/BeaconChain.tsx`

## Notas
Sprint UI wiring pós-auditoria 2026-05-23.

# BCN-230 — UI wire BeaconOverview

**Owner**: frontend
**Estimativa**: S (2-4h)
**Pré-requisitos**: `apps/beacon-ui/src/lib/api.ts` (existe), endpoint `/v1/overview`

## Definição

Substituir mock data em `apps/beacon-ui/src/pages/beacon/BeaconOverview.tsx` por fetch real ao backend via TanStack Query.

Steps:
1. Criar/usar hook `apps/beacon-ui/src/lib/hooks/use-overview.ts` (TanStack Query)
2. Endpoint backend: `GET /v1/overview` (já implementado conforme [[BCN-151]])
3. Remover import de mock data (`@/content/beacon-mock`)
4. Render via `hook.data` com fallback `useQuery({ initialData: mock_fallback })`
5. Banner amarelo "Modo demo" se `hook.isError` (graceful degradation V0)

## Critérios de aceite

- [ ] Page carrega dado real do backend quando rodando
- [ ] Fallback mock quando backend não responde
- [ ] Skeleton loading via `hook.isLoading`
- [ ] Error state com toast/banner
- [ ] Sem `import mock from "@/content/beacon-mock"` (ou só como fallback)

## Referências

- Backend endpoint: [[BCN-151]]
- Gold standard pattern: `apps/pulse-cloud-ui/src/lib/pulseApi.ts`
- Cliente HTTP: `apps/beacon-ui/src/lib/api.ts`
- Page atual: `apps/beacon-ui/src/pages/beacon/BeaconOverview.tsx`

## Notas

Parte do sprint UI wiring pós-auditoria 2026-05-23. Gap identificado: rewire-beacon com 0/19 pages wired no consumo real (BCN-150 codegen OK, hooks não plugados ainda).

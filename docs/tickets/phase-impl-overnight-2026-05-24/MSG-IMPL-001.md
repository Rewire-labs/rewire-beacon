# MSG-IMPL-001 - Frontend wiring (rewire-messaging)

**Owner agente**: Sync Agent #2 ou Lote 8 sub-lote N
**Estimativa**: 1d
**Status**: TODO
**Pre-requisitos**: Lovable telas DELIVERED (ver services/PROMPTS_LOVABLE_TRACKING.md)

## Definicao

Wire frontend rewire-messaging com:
1. HTTP client + TanStack Query setup (lib/api.ts, lib/queryClient.ts) - pattern ASC-100
2. Providers wrap em main.tsx (QueryClientProvider + AuthProvider Authentik OIDC)
3. Hooks per recurso principal (useMSG*, e.g., useDashboard, useList, useDetail, useCreate, useUpdate, useDelete)
4. Error boundaries (ApiError RFC 7807)
5. Loading + empty + error states per page
6. PT-BR i18n por padrao (en-US opcional)
7. Telas Lovable connectadas a hooks (substituir mocks)

## Acceptance criteria

- [ ] lib/api.ts exporta api<T>() + ApiError + ApiResponse
- [ ] lib/queryClient.ts singleton com defaults sensatos (staleTime, retry, refetchOnWindowFocus)
- [ ] Providers wrap main.tsx
- [ ] Pelo menos 5 hooks principais funcionais (mock backend OK ate IMPL-002 done)
- [ ] Error boundaries cobertura 100% pages
- [ ] Telas Lovable renderizam dados reais (nao mocks hardcoded)
- [ ] npm run build sem warnings
- [ ] npm test passa basicos
- [ ] PT-BR labels nas pages principais

## Referencias

- Gold standard: services/rewire-pulse/apps/pulse-ui/src/lib/pulseApi.ts
- Pattern auth: services/rewire-app/apps/app-portal/src/lib/auth.ts
- UX simplificacao: services/rewire-messaging/prompt_lovable_simplificacao.md (deletado se DELETED em tracking)
- UX_ANALYSIS_LOVABLE.md: services/rewire-messaging/UX_ANALYSIS_LOVABLE.md

## Notas

Foundation bloqueia tudo seguinte. Wire mocks ate MSG-IMPL-002 entregar backend real.
Commit PT-BR: feat(rewire-messaging): frontend wiring hooks + providers + error boundaries (phase-impl-overnight)


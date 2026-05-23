# BCN-150 — OpenAPI codegen TypeScript client (consumido pelo beacon-ui)

**Owner**: frontend
**Estimativa**: M (1d)
**Pré-requisitos**: [[BCN-227]] OpenAPI spec dump em
`docs/api/openapi.yaml`

## Definição

Gerar cliente TypeScript a partir de `docs/api/openapi.yaml` para uso
pelo `apps/beacon-ui/` (19 pages Lovable). Substituir mocks em
`src/content/beacon-mock.ts` por chamadas reais conforme phase 13
tickets [[BCN-151]]-[[BCN-168]].

Toolchain candidato: `openapi-typescript` + `openapi-fetch` (minimal) ou
Orval (gera React Query hooks).

## Critérios de aceite

- [ ] Script `npm run codegen` (em `apps/beacon-ui/package.json`) gera
  `src/api/types.ts` + `src/api/client.ts` a partir da spec
- [ ] CI check valida `git diff --exit-code` após codegen (drift detection)
- [ ] Types incluem todos endpoints + schemas Pydantic
- [ ] React Query hooks (Orval) ou wrappers manuais `useQuery`/`useMutation`
- [ ] Interceptor 401 redireciona para login
- [ ] Interceptor anexa `Authorization: Bearer <jwt|api_token>`
- [ ] Org switcher: header `X-Organization-Id` auto-anexado para tokens
  cross-org
- [ ] Documentação no `apps/beacon-ui/README.md`

## Referências

- [docs/api/API_SPEC.md](../../api/API_SPEC.md) — base do contrato
- [ADR 0003 — Auth pattern (JWT + API tokens)](../../adr/0003-auth-authentik-oidc-api-tokens.md)
- [[BCN-227]] OpenAPI dump backend
- 19 pages tickets [[BCN-151]] a [[BCN-168]]

## Notas implementação

- Mocks em `beacon-mock.ts` removidos progressivamente conforme cada
  page é wirada (não remover de uma vez — quebraria pages não-wired)
- Lovable projeto separado: codegen roda local antes de sync PR
- React Query staleTime conservador (60s default) para pages analytics
- RFC 7807 error handling (problem+json) — interceptor formata friendly

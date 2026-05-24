# MSG-IMPL-003 - Tests (rewire-messaging)

**Owner agente**: Lote 8 sub-lote N
**Estimativa**: 0.5d
**Status**: TODO
**Pre-requisitos**: MSG-IMPL-001 + MSG-IMPL-002 done

## Definicao

Cobertura testes minima rewire-messaging:
1. **pytest unit** (backend): cada endpoint CRUD + auth + tenant isolation + edge cases (404, 401, 422)
2. **jest unit** (frontend): cada hook (mock fetch) + error boundary triggers
3. **pytest integration** (backend + DB): testar migrations + queries reais (Postgres testcontainer ou sqlite)
4. **smoke E2E** (Playwright opcional): 1-3 fluxos principais ponta-a-ponta (mock auth)
5. **CI config** (Gitea Actions workflow): roda pytest + jest + lint + build em PR

## Acceptance criteria

- [ ] pytest cobre >=80% endpoints (pytest --cov)
- [ ] jest cobre >=70% hooks principais
- [ ] Integration tests testam migration up + down + schema sanity
- [ ] Smoke E2E roda 1+ fluxo principal happy path
- [ ] CI workflow .gitea/workflows/test.yaml passa em PR
- [ ] Tests sao deterministicos (no flaky)

## Referencias

- Gold standard: services/rewire-ascend/apps/ascend-api/tests/ (61 tests Round A)
- Pytest pattern: services/rewire-pulse/apps/pulse-api/tests/test_endpoints.py
- Jest pattern: services/rewire-pulse/apps/pulse-ui/src/lib/__tests__/pulseApi.test.ts
- ADR 0098 (smoke tests canonical V0)

## Notas

Foco em deterministic + fast (<60s suite total). Sem cluster real (mock externos).
Commit PT-BR: feat(rewire-messaging): tests pytest + jest + smoke E2E (phase-impl-overnight)


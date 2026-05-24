# MSG-IMPL-005 - Smoke tests + integracao cross-product (rewire-messaging)

**Owner agente**: Lote 8 sub-lote N (final)
**Estimativa**: 0.5d
**Status**: TODO (BLOCKED ate MSG-IMPL-004 deployed)
**Pre-requisitos**: MSG-IMPL-004 done + recovery cluster runtime done

## Definicao

Validacao end-to-end rewire-messaging no cluster:
1. **Smoke health** via installer API endpoint (ADR 0110: /api/v1/recovery/diagnose checa rewire-messaging)
2. **Auth flow** Authentik OIDC: login -> callback -> page protegida render OK
3. **CRUD basico** atraves UI ate DB Postgres CNPG (verificar via rewire-messaging backend logs)
4. **Cross-product integracao** principais (refs nomes NOVOS ADR 0108):
   - Auth via rewire-auth (token bearer)
   - Logs via rewire-pulse (Loki query)
   - Metrics via rewire-pulse (Prometheus scrape funcionando)
   - Audit log via rewire-audit (append-only)
5. **Reconciler scan** (ADR 0111): pattern scanner detecta rewire-messaging healthy (sem findings)

## Acceptance criteria

- [ ] Installer diagnose endpoint reporta rewire-messaging OK
- [ ] OIDC login fluxo funciona (manual smoke via browser)
- [ ] CRUD basico funcional (criar 1 item, listar, editar, deletar)
- [ ] Logs rewire-messaging aparecem em Loki (namespace query)
- [ ] Metrics rewire-messaging aparecem em Prometheus (job label)
- [ ] Audit log rewire-messaging register acoes principais
- [ ] Reconciler /reconciler/coverage mostra rewire-messaging sem findings

## Referencias

- ADR 0110 (installer endpoints /api/v1/recovery/diagnose)
- ADR 0111 (reconciler auto-recovery loop)
- ADR 0107 (Central AI Chat orchestrator) - se rewire-messaging expoe capability via MCP
- services/INTER_AGENT_COMM_SPEC.md (se rewire-messaging participa A2A)

## Notas

Ticket final do phase. Marca produto como PRODUCTION-READY no tracking dashboard.
Commit PT-BR: feat(rewire-messaging): smoke tests + integracao cross-product validados (phase-impl-overnight)


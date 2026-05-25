# Phase Impl Overnight 2026-05-24 - rewire-messaging

> Phase de implementacao overnight 2026-05-24 disparada pelo Cluster Tracking & ADR Agent.
> Cobre 5 tickets sequenciais por produto pos-Lovable simplificacao (ADR 0108) + alinhado ADRs 0109/0110/0111.

## Produto
**rewire-messaging** - Messaging (email+SMS+push+WhatsApp, consolidacao notify+beacon)

## Contexto Lovable
- Lovable status: pending Lovable processing (commit 7c744bb)
- Prompt simplificacao SENT: 2026-05-24
- Telas Lovable: ver UX_ANALYSIS_LOVABLE.md + prompt_lovable_simplificacao.md
- Ver tracking: services/PROMPTS_LOVABLE_TRACKING.md + services/CLUSTER_IMPLEMENTATION_TRACKING.md

## Escopo overnight
frontend messaging-ui + backend Python email (Resend) + SMS + APNs/FCM + WhatsApp CONNECT

## Tickets

| ID | Titulo | Estimativa | Owner agente | Status |
|---|---|---|---|---|
| MSG-IMPL-001 | Frontend wiring (hooks, providers, error boundaries) | 1d | Lote 8 Implementador rewire-messaging | DONE (lib/api.ts ampliado + useMessaging* hooks + 2 telas novas BeaconAbTests/BeaconSegments + rotas /ab-tests + /segments) |
| MSG-IMPL-002 | Backend stubs (FastAPI/Go endpoints + migrations Alembic) | 1.5d | Lote 8 Implementador rewire-messaging | DONE (dispatcher umbrella /v1/notifications + /v1/channels + 2 novos routers /v1/ab-tests + /v1/segments; messages backend pre-existente preservado) |
| MSG-IMPL-003 | Tests (pytest unit + jest unit + smoke) | 0.5d | Lote 8 Implementador rewire-messaging | DONE (21 tests novos green: 6 ab-tests + 5 segments + 6 dispatcher + 3 smoke + 1 healthz auth) |
| MSG-IMPL-004 | Helm chart + ArgoCD App + ExternalSecrets | 0.5d | Lote 8 Implementador rewire-messaging | DONE-PRE-RECOVERY (helm lint clean + helm template render OK 508 lines + ApplicationSet entry confirmada; deploy real gated por recovery cluster runtime ADR 0110) |
| MSG-IMPL-005 | Smoke tests + integracao cross-product | 0.5d | Lote 8 Implementador rewire-messaging | DONE-PRE-RECOVERY (smoke E2E local + scripts/smoke-tests/messaging/test_smoke.py 8 cluster smoke tests prontos para rodar pós-recovery) |

## Acceptance criteria global (todos tickets)

- [ ] Codigo committado main only (sem branches isoladas)
- [ ] Commits PT-BR (feat(rewire-messaging): ...)
- [ ] Sem secrets em commit messages
- [ ] Cross-product refs usam nomes NOVOS (ADR 0108)
- [ ] Atualizado tracking: services/CLUSTER_IMPLEMENTATION_TRACKING.md + services/PROMPTS_LOVABLE_TRACKING.md

## Bloqueadores

- MSG-IMPL-004 (Deploy) bloqueado por recovery cluster runtime (Vault/CF/Authentik/Harbor/ArgoCD)
- MSG-IMPL-005 (Integracao) bloqueado por MSG-IMPL-004 done

## Cross-refs

- ADR 0108 (products naming consolidation)
- ADR 0109 (pipeline overnight autonomo)
- ADR 0110 (installer endpoints composite recovery)
- ADR 0111 (reconciler auto-recovery loop)
- services/AUTONOMOUS_OVERNIGHT_PLAN.md
- services/CLUSTER_IMPLEMENTATION_TRACKING.md
- services/PROMPTS_LOVABLE_TRACKING.md
- services/ECOSYSTEM_INTERDEPENDENCIES.md


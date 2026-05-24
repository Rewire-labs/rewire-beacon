# MSG-IMPL-004 - Helm + ArgoCD + ExternalSecrets (rewire-messaging)

**Owner agente**: Lote 8 sub-lote N
**Estimativa**: 0.5d
**Status**: TODO (BLOCKED ate recovery cluster runtime ADR 0110)
**Pre-requisitos**: MSG-IMPL-002 backend buildavel (Docker image) + cluster recovery done

## Definicao

Deploy rewire-messaging GitOps:
1. **Helm chart** em charts/rewire-messaging/ (Chart.yaml v0, values.yaml, templates/)
2. **Deployment** + Service + Ingress (Authentik forward-auth ADR 0101)
3. **HPA** + PDB (minAvailable=2 prod, 1 staging)
4. **ExternalSecrets** apontando Vault paths NOVOS (ADR 0108: secret/rewire/rewire-messaging/*)
5. **ConfigMap** values app
6. **NetworkPolicy** Cilium (allow ingress controller + Authentik + dependencies)
7. **ServiceMonitor** Prometheus scrape /metrics
8. **ArgoCD Application** em argocd/apps/rewire-messaging.yaml (sync wave order correto)
9. **Smoke health** check pos-deploy (curl /healthz)

## Acceptance criteria

- [ ] helm lint charts/rewire-messaging/ sem erros
- [ ] helm template renderiza YAML valido
- [ ] kubectl apply --dry-run aceita sem erros (sintatico)
- [ ] ExternalSecrets criados (status SecretSynced)
- [ ] ArgoCD App sync OK (status Healthy + Synced)
- [ ] Ingress responde TLS (cert-manager wildcard ADR 0091)
- [ ] /healthz responde 200 atraves ingress
- [ ] HPA scale-up funciona sob load test simples

## Referencias

- ADR 0095 (products helm charts canonical V0)
- ADR 0091 (cert-manager wildcard DNS-01 canonical V0)
- ADR 0101 (Authentik forward-auth platform UIs)
- ADR 0086 (Cilium mTLS SPIRE canonical V0.1)
- ADR 0110 (installer endpoints composite recovery) - recovery bloqueia este ticket ate done

## Notas

BLOQUEADO ate recovery cluster runtime (Vault paths + CF DNS + Authentik OIDC clients + Harbor images + ArgoCD sync). Ver tracking services/CLUSTER_IMPLEMENTATION_TRACKING.md secao 2.
Commit PT-BR: feat(rewire-messaging): helm chart + ArgoCD App + ExternalSecrets (phase-impl-overnight)


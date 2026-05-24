# BCN-V2001 — Helm chart control-plane completo (Deployment+HPA+PDB+PrometheusRule)

**Owner**: infra + backend BEACON
**Estimativa**: M (1 sprint)
**Pré-requisitos**: imagem Docker buildada/pushed para registry
**Detected by**: audit pass-2 (2026-05-24)

## Contexto

BEACON tem `cluster/*.yaml` para ExternalSecret/Authentik/Kong/ServiceMonitor/
NetworkPolicy/MinIO mas NÃO tem Helm chart próprio. Não há:
- `deploy/helm/beacon/templates/deployment.yaml` (control-plane API)
- `deploy/helm/beacon/templates/worker-deployments.yaml` (email/sms/push/wa senders)
- HPA + PDB
- PrometheusRule SLO crítico
- Chart.yaml + values.yaml + values-dev/v0.yaml

Comparar com PULSE-CLOUD/CITADEL-CLOUD — ambos têm Helm chart completo.

## Definição

1. `deploy/helm/beacon/` estrutura canonical:
   - Chart.yaml
   - values.yaml + values-dev.yaml + values-v0.yaml
   - templates/_helpers.tpl
   - templates/deployment-control-plane.yaml
   - templates/worker-deployments.yaml (4 workers: email/sms/push/wa)
   - templates/temporal-worker-deployment.yaml
   - templates/service.yaml + ingress.yaml + serviceaccount.yaml
   - templates/hpa.yaml + pdb.yaml
   - templates/externalsecret.yaml (consolidar `cluster/external-secrets.yaml`)
   - templates/servicemonitor.yaml + prometheusrule.yaml
   - templates/networkpolicy.yaml
   - templates/applicationset.yaml (ArgoCD)
2. PrometheusRule SLO:
   - `BeaconControlPlaneDown` up==0 5m → critical
   - `BeaconHighErrorRate` 5xx > 1% → warning
   - `BeaconEmailDeliveryStalled` queue depth > 10k → critical
   - `BeaconChainAnchorBroken` audit_chain_integrity==0 → critical
   - `BeaconSuppressionLatencyHigh` p95 > 50ms → warning
   - `BeaconPostalBounceRateHigh` per tenant > 5% 1h → page tenant owner
3. ServiceMonitor consolidado em chart (remover `cluster/observability.yaml` legacy).

## Critérios de aceite

- [ ] `helm install beacon ./deploy/helm/beacon -f values-v0.yaml --dry-run` passes
- [ ] ArgoCD ApplicationSet sync ok cluster-dev
- [ ] 6+ PrometheusRules acionando em smoke test fault injection
- [ ] CHANGELOG.md updated

## Referências

- BCN-180..186 (cluster manifests fragments) — refactor para chart
- ADR-0005 cluster integration patterns

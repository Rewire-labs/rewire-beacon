# NTF-014 — Helm chart prod values (observability namespace, wave 5)

- **Owner**: @alessandro
- **Estimativa**: M
- **Pre-reqs**: cluster Fase 3 (Vault prod + Authentik)
- **Status**: [x] done estrutura (`deploy/helm/rewire-notify/`)

## Definicao

Helm chart em `deploy/helm/rewire-notify/`:

- Deployment 1 replica (V0.1, multi-pod aguarda [[NTF-011]]).
- Service ClusterIP.
- ServiceAccount + RBAC minimal.
- ExternalSecret refs Vault `kv/rewire/notify/telegram-*`.
- NetworkPolicy (egress: Kafka, Lago, Foundry, Telegram, Vault).
- Resource requests/limits.
- ApplicationSet entry em `observability.yaml` wave 5.

## Aceite

- [x] Chart.yaml versionado.
- [x] `values.yaml` defaults.
- [ ] `values-prod.yaml` overlay.
- [x] `templates/deployment.yaml`, `service.yaml`, `externalsecret.yaml`.
- [ ] NetworkPolicy egress whitelist.
- [ ] ArgoCD Application standalone `deploy/argocd/application.yaml`.

## Refs

- [ADR 0007](../../adr/0007-external-secret-vault-telegram.md)
- [ADR 0008](../../adr/0008-argocd-observability-namespace.md)
- `deploy/helm/rewire-notify/`

## Notas

NetworkPolicy + values-prod overlay sao gaps abertos.

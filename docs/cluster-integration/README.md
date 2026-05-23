# Cluster integration — BEACON

Documentação de integração com cluster Rewire (Kubernetes + ArgoCD).

| Doc | Descrição |
|---|---|
| `00-overview.md` | Visão geral arquitetura BEACON no cluster |
| `01-namespaces.md` | Namespace `beacon` + labels canonical |
| `02-secrets.md` | Vault paths + ExternalSecret CRDs |
| `03-networking.md` | Kong routes + NetworkPolicies |
| `04-observability.md` | ServiceMonitor + OTLP + Grafana dashboards |

Manifests aplicáveis em `cluster/`:

- `external-secrets.yaml` — ESO CRDs para Vault → Secret
- `networking.yaml` — Kong Ingress + NetworkPolicy
- `observability.yaml` — ServiceMonitor + PodMonitor + OTLP ConfigMap
- `storage.yaml` — MinIO Tenant buckets + Postgres backup CronJob
- `authentik.yaml` — OIDC client blueprint

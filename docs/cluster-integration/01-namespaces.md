# Cluster integration — Namespaces

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: beacon
  labels:
    kubernetes.io/metadata.name: beacon
    rewire.io/product: beacon
    rewire.io/tier: business
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

## Labels canonical para selectors cross-namespace

- `app.kubernetes.io/name`: beacon-control-plane | beacon-email-sender | ...
- `app.kubernetes.io/component`: api | worker | cron | ui
- `app.kubernetes.io/part-of`: beacon
- `app.kubernetes.io/managed-by`: argocd
- `rewire.io/tier`: hobby | starter | scale | enterprise (per worker tier)

## Naming convention

`beacon-<role>[-<channel>][-<tier>]`:
- `beacon-control-plane` (API)
- `beacon-email-sender-starter` (Kafka consumer)
- `beacon-push-sender-android-enterprise`

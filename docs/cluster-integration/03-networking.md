# Cluster integration — Networking

## Ingress (Kong)

| Host | Backend Service | Cert |
|---|---|---|
| `api.beacon.rewirelabs.dev` | `beacon-control-plane:8080` | Let's Encrypt prod |
| `app.beacon.rewirelabs.dev` | `beacon-ui:80` | Let's Encrypt prod |

## NetworkPolicies

Default-deny em todo namespace `beacon`. Allows explícitos:

### Ingress permitido

- Kong → control-plane:8080 (HTTP routes)
- Connect/Foundry/Host/Audit-Trail/Guardian (cross-product internal) → control-plane:8080

### Egress permitido

- DNS (kube-system:53)
- Cluster services (postgres, redis, redpanda, clickhouse, temporal, vault, minio)
- External 443/25/587/2525 (SMTP relay, BSPs, APNs, FCM)

## Cross-product internal endpoints

| Endpoint | Quem chama | Quem implementa |
|---|---|---|
| `POST /v1/messages/email` | Foundry/Host/Audit | BEACON |
| `POST /connect/internal/v1/whatsapp/send` | BEACON (worker) | CONNECT |
| `POST /chain/append` | BEACON (audit chain) | CITADEL |
| `POST /audit/evidence` | BEACON | AUDIT-TRAIL |

Authentication cross-product: mTLS via cluster CA + header `X-Source-Service`.

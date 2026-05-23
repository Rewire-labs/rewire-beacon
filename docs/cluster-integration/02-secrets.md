# Cluster integration — Secrets

Todos os secrets são materializados via ExternalSecret CRDs (ESO).

## Vault paths

| Path | Conteúdo |
|---|---|
| `secret/rewire/beacon/database` | `url`, `worker_url` |
| `secret/rewire/beacon/redis` | `url` |
| `secret/rewire/beacon/oidc` | `client_secret` |
| `secret/rewire/beacon/postal` | `api_key`, `webhook_secret` |
| `secret/rewire/beacon/zenvia` | `api_token` |
| `secret/rewire/beacon/totalvoice` | `api_token` |
| `secret/rewire/beacon/aws-ses` | `access_key_id`, `secret_access_key` |
| `secret/rewire/beacon/lago` | `api_key` |
| `secret/rewire/beacon/asaas` | `api_key` |
| `secret/rewire/beacon/nfeio` | `api_key`, `company_id` |
| `secret/rewire/beacon/unsubscribe` | `secret` (HMAC key) |
| `secret/rewire/beacon/orgs/<org_id>/apns` | `.p8` blob + `key_id`, `team_id` |
| `secret/rewire/beacon/orgs/<org_id>/fcm` | service account JSON |
| `secret/rewire/beacon/orgs/<org_id>/vapid` | private key PEM |

## Rotation

- Cluster-wide (Postal, Zenvia, etc): 90d rotation via Vault transit engine
- Per-org (APNs/FCM/VAPID): cliente faz upload via UI, BEACON nunca vê plaintext após gravação inicial

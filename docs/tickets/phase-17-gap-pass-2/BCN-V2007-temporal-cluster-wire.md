# BCN-V2007 — Temporal cluster wire compartilhado (BCN-100)

**Owner**: infra + backend
**Estimativa**: M (1 sprint)
**Pré-requisitos**: Temporal cluster shared cluster-wide deployed
**Detected by**: audit pass-2 (2026-05-24, ainda em backlog BCN-100)

## Contexto

BCN-100 marked [ ]: Temporal cluster setup compartilhado. Workflows
(BCN-101/102/103/105/106) já implementados mas worker entrypoint
não conectado a Temporal cluster real.

## Definição

1. Confirmar Temporal cluster endpoint cluster-wide:
   `temporal-frontend.rewire-temporal.svc:7233`
2. Helm sub-chart `beacon-temporal-worker`:
   - Deployment `Worker(client, task_queue="beacon-default", workflows=[MultiChannelJourneyWorkflow], activities=[send_email_act, send_sms_act, ...])`
   - Replicas 3 (HA)
   - ExternalSecret `secret/rewire/beacon/temporal-tls` (mTLS client cert)
3. Schedules Temporal criados via `schedule.create`:
   - `beacon.bounce_reaper`: cron `*/15 * * * *`
   - `beacon.suppression_warmup`: cron `0 4 * * *`
4. Namespace Temporal `beacon` registered.
5. Métricas `temporal_worker_*` exposed via PodMonitor.

## Critérios de aceite

- [ ] Workflows visible em Temporal UI
- [ ] Activity execution success rate >99%
- [ ] Schedules running daily/15min
- [ ] mTLS handshake ok

## Referências

- BCN-100 (original)
- BCN-101/102/103 workflows existentes

# Runbook — Postal incident

## Sintomas

- Spike em `beacon.deliveries.status = 'failed'` com `provider='postal'`
- `/healthz` do Postal retornando 5xx
- Kafka topic `beacon.send.email.*` com lag > 10k

## Diagnose

```bash
kubectl -n beacon get pods -l app=postal
kubectl -n beacon logs -l app=postal --tail=100
kubectl -n beacon exec -it postal-0 -- /opt/postal/bin/postal status
```

## Mitigação

### Curto prazo (< 5min)

1. Workers `email_sender` (tier scale/enterprise) já fazem fallback automático para AWS SES.
2. Workers `email_sender` (tier hobby/starter) precisam fallback manual:
   ```bash
   kubectl -n beacon set env deploy/beacon-email-sender-hobby BEACON_FORCE_SES=1
   ```

### Médio prazo (< 30min)

3. Restart Postal nodes em rolling:
   ```bash
   kubectl -n beacon rollout restart statefulset/postal
   ```

4. Verificar DB Postal (MySQL embarcado / separate):
   ```bash
   kubectl -n beacon exec -it postal-mysql-0 -- mysql -e "SHOW PROCESSLIST"
   ```

### Longo prazo (root cause)

5. Análise de logs: spam outbreak? IP blacklisted? DB lock?
6. Se IP comprometida → mover org afetadas para outro IP:
   ```sql
   UPDATE senders.email_domains SET postal_vhost_id = 'vhost-new'
   WHERE postal_vhost_id = 'vhost-bad';
   ```

## Comunicação

- Status page: `https://status.beacon.rewirelabs.dev`
- Slack `#beacon-ops`
- Customer notification se SLA breach (>15min) via BeaconWebhooks subscribers

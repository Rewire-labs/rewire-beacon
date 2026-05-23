# Runbook — DSAR export deadline (LGPD 15 dias)

## Contexto

LGPD Art. 18 garante ao titular o direito de obter dados pessoais
processados. ANPD interpreta como 15 dias úteis para resposta.

BEACON dispara DSAR via `POST /v1/audit/lgpd/dsar` que cria background
job. Target interno: 24h. SLA legal: 15 dias.

## Monitoring

Query DSARs pendentes:

```sql
SELECT id, recipient, created_at, payload->>'status' AS status
FROM beacon.notifications
WHERE channel_kind = 'dsar_request'
  AND (payload->>'status') != 'completed'
  AND created_at < now() - interval '24 hours';
```

Se rows retornadas → atrasados, escalar.

## Mitigação atrasos

### Job travado

```bash
# Verificar workers
kubectl -n beacon get pods -l app.kubernetes.io/component=dsar-worker

# Restart se necessário
kubectl -n beacon rollout restart deploy/beacon-dsar-worker
```

### Volume excedendo throughput

Aumentar replicas:
```bash
kubectl -n beacon scale deploy/beacon-dsar-worker --replicas=5
```

### ClickHouse query lenta

Adicionar índice secundário em `beacon_events.messages`:
```sql
ALTER TABLE beacon_events.messages
  ADD INDEX idx_recipient_bloom recipient TYPE bloom_filter GRANULARITY 4;
```

## Output expected

JSON com schema:
```json
{
  "dsar_id": "dsar-...",
  "organization_id": "...",
  "exports": {
    "email_notifications": [...],
    "suppression": [...],
    "events": [...]
  }
}
```

Armazenado em MinIO `beacon-evidence/dsar/<id>.json` (encrypted, signed URL).

## Notificação ao titular

Sistema envia email automático para o titular com link assinado válido 7 dias.

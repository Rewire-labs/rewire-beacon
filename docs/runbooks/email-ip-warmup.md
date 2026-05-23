# Runbook — Email IP warmup

## Quando aplicar

- Provisionamento de IP dedicado novo no pool Postal
- Migração de IP entre Postal nodes
- Recuperação de reputation post-incident (drop > 20 pontos)

## Processo (30 dias)

### Pré-requisitos
- IP entrou em `senders.dedicated_ips` com `warmup_status='cold'`
- DNS PTR record configurado (`<ip>.in-addr.arpa.` → `mailer-<n>.beacon.rewirelabs.dev`)
- SPF/DKIM/DMARC do domínio validados

### Dia 1-7: Cold start
- `current_daily_cap = 50` mensagens/dia
- Enviar apenas para opt-in confirmados (high engagement)
- Monitorar bounce/complaint rate via `GET /v1/analytics/messages?channel=email`
- Threshold abort: bounce > 5% OR complaint > 0.1% → pause warmup

### Dia 8-14: Ramp 2x/dia
- Aumentar daily_cap dobrando: 100, 200, 400, 800, 1600, 3200, 6400
- Reputation score deve subir para 65+ (monitorar `reputation_score` em senders.dedicated_ips)

### Dia 15-30: Linear ramp
- +50% por dia: 9600, 14400, 21600, ...
- Atingir `warmup_target_daily` (default 50k)
- Bump `warmup_status='warm'` quando estável 3 dias

## Comandos úteis

```sql
-- Status atual
SELECT ip_address, warmup_status, current_daily_cap, reputation_score
FROM senders.dedicated_ips WHERE warmup_status IN ('cold','warming');

-- Pause manual
UPDATE senders.dedicated_ips SET warmup_status = 'blocked' WHERE ip_address = 'X.X.X.X';

-- Volumes últimas 24h por IP
SELECT count(*) FROM beacon.deliveries d
JOIN beacon.notifications n ON n.id = d.notification_id
WHERE n.channel_kind = 'email' AND d.last_attempt_at > now() - interval '24h';
```

## Escalação

- Reputation < 40 por 2h → page on-call deliverability
- Postal node `messages_pending` > 10k → page infra

# Runbook — Anti-spam false positive

## Quando

- Cliente reporta mensagem rejeitada com 451 `blocked_antispam`
- Score reportado >= 60 mas conteúdo legítimo

## Diagnose

1. Reproduzir score via API:
   ```bash
   curl -X POST https://api.beacon.rewirelabs.dev/v1/antispam/score \
     -H "Authorization: Bearer <token>" \
     -d '{"content":"<conteudo>","recipients_count":1}'
   ```
2. Inspecionar `reasons` no response.

## Mitigação imediata

### Whitelist pattern

```bash
curl -X POST https://api.beacon.rewirelabs.dev/v1/antispam/whitelist \
  -H "Authorization: Bearer <token>" \
  -d '{"pattern":"<keyword ou regex>"}'
```

### Re-tentar envio

Cliente reenvia mensagem; deve passar agora.

## Análise

- Log do `BEACON_ANTISPAM_ALERT_WEBHOOK` no Slack ops
- Categorizar false positive em:
  - keyword genérico (ex: "promoção" usado por e-commerce legítimo)
  - tenant novo + volume legítimo
  - bounce rate alto temporariamente (DNS misconfig)

## Ajuste do score

Se padrão recorrente:
1. Editar `SPAM_KEYWORDS` em `services/antispam.py`
2. Ajustar thresholds em `_score_tenant_history`
3. Commit + deploy via CI

## Compensação ao cliente

Se >5 false positives no mês, oferecer crédito proporcional via Lago.

# ADR 0005 — Daily digest 09:00 BRT via APScheduler

- **Status**: Accepted
- **Data**: 2026-05-18
- **Decisores**: Alessandro Queiroz

## Contexto

Operador precisa de visao consolidada diaria: que crashloops aconteceram
ontem, quanto Lago billou, quantos PRs Foundry mergearam, etc. Pull on
demand via `/daily` command + push automatico 09:00 BRT.

Sem scheduled push, operador esquece de checar.

## Decisao

Implementar **APScheduler** em background task que dispara
`run_daily_digest` cron 09:00 BRT (`Settings.daily_digest_cron_hour_brt=9`).

Agregator consulta:
- Lago `/api/v1/events` ontem.
- Foundry `/api/v1/prs?merged=true&since=24h`.
- Alertmanager `/api/v2/alerts` open.
- Health checks 18 produtos (V0.1 stubbed).

Resultado formatado em template `daily.summary` event kind.

## Alternativas consideradas

1. **Kubernetes CronJob separate**
   - Pros: K8s-nativo.
   - Contras: separate Deployment, complexity; in-process eh OK pra
     single pod.
   - Descartada: APScheduler mais simples.

2. **Sem digest (apenas `/daily` on-demand)**
   - Pros: zero cron.
   - Contras: operador esquece — defeitos passam dias sem notar.
   - Descartada.

3. **Temporal scheduled workflow**
   - Pros: durable.
   - Contras: cluster Temporal dep para single notif; overkill.
   - Descartada.

## Consequencias

- **Positivas**: APScheduler in-process simples; configuravel BRT;
  `/daily` command forca-fire imediato.
- **Negativas**: single pod = SPOF (multiple pods exigiria distributed
  lock para evitar duplicate digest); restart pode pular cron se cair
  proximo da hora.
- **Neutras**: V0.1 tier acceptable.

## Proximas acoes

- Ticket [[NTF-007]] — wire endpoints reais Lago/Foundry/Alertmanager.
- Ticket [[NTF-011]] — multi-pod distributed lock (Redis).

## Referencias

- `src/rewire_notify/daily_digest.py`
- `src/rewire_notify/settings.py`

## Historico de revisoes

| Data | Autor | Mudanca |
|---|---|---|
| 2026-05-23 | audit-agent | criacao retroativa |

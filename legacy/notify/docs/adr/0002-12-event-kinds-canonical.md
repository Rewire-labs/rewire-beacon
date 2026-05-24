# ADR 0002 — 12 event kinds canonicos + routing rules

- **Status**: Accepted
- **Data**: 2026-05-18
- **Decisores**: Alessandro Queiroz
- **Consulta tecnica**: `rewire_shared/notify/telegram/events.EventKind`

## Contexto

Sem taxonomia fixa de eventos, cada producer (Alertmanager, Redpanda
topics, scheduled jobs, ad-hoc POST) emite shapes diferentes — formatter
ruim, routing inconsistente.

## Decisao

Definir **12 event kinds canonicos** em
`rewire_shared.notify.telegram.events.EventKind`:

| kind | severity | inline keyboard |
|----------------------------|----------|-----------------|
| `tenant.onboarded` | info | — |
| `asaas.payment_received` | info | — |
| `product.crashloop` | critical | — |
| `vault.sealed` | critical | View Unseal Runbook |
| `breach.detected` | critical | View Workflow |
| `tenant.hard_cap_exceeded` | warn | Notify Customer / Increase Cap |
| `lgpd.dsar.requested` | warn | — |
| `foundry.pr.merged` | info | — |
| `daily.summary` | info | — |
| `smoke.test.failed` | critical | — |
| `cost.anomaly` | warn | — |
| `pricing.change.applied` | warn | — |

Formatter registry `rewire_shared.notify.telegram.formatter` mapeia
kind→template.

**Routing rules**:
- `critical` → operator's PV AND Rewire Labs group (PV push priority).
- `warn` / `info` → group only, silent.
- `vault.sealed`, `breach.detected`, `product.crashloop`,
  `smoke.test.failed` → ALWAYS both chats (defensive override).

## Alternativas consideradas

1. **Kind livre (no taxonomy)**
   - Pros: zero coupling.
   - Contras: cada producer reinventa; sem formatter consistente.
   - Descartada.

2. **JSON Schema OpenAPI shared**
   - Pros: validation rigoroso.
   - Contras: overhead pra evolutivo.
   - Descartada: 12 kinds enum eh mais simples.

## Consequencias

- **Positivas**: formatter cada kind tem template proprio (i18n PT-BR
  + emojis); routing previsivel; novo kind exige PR shared lib.
- **Negativas**: enum closed — adding kind exige bump shared.
- **Neutras**: Alertmanager synthetic mapping (alertname → kind) em
  `dispatcher.alertmanager_payload_to_events`.

## Proximas acoes

- Ticket [[NTF-005]] — eventos producer canonicos por cross-product.
- Doc shared lib `rewire_shared/notify/telegram/`.

## Referencias

- `src/rewire_notify/dispatcher.py`
- `rewire_shared/notify/telegram/events.py`
- README.md secao "12 supported event kinds"

## Historico de revisoes

| Data | Autor | Mudanca |
|---|---|---|
| 2026-05-23 | audit-agent | criacao retroativa |

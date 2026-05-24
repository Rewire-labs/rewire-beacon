# ADR 0006 — Bot command poller long-poll `getUpdates`

- **Status**: Accepted
- **Data**: 2026-05-18
- **Decisores**: Alessandro Queiroz

## Contexto

Operador precisa interagir bot via comandos (`/status`, `/daily`,
`/alerts`, `/help`). 2 caminhos Telegram: **webhook** (Telegram chama
nosso endpoint) ou **long-poll** (nos chamamos `getUpdates`).

Webhook exige HTTPS publico + cert validado por Telegram. Long-poll
funciona atras de NAT/cluster-internal.

## Decisao

Adotar **long-poll** via `TelegramAdapter.getUpdates` em background
task (`BotCommandPoller`). Timeout 25s (Telegram max 50s). Chat
authorization: apenas PV operador + grupo Rewire Labs.

## Alternativas consideradas

1. **Webhook**
   - Pros: real-time, sem polling.
   - Contras: HTTPS publico (precisa Cloudflare Tunnel + cert);
     setup mais complexo; cluster intern preferable.
   - Descartada: complexity.

2. **Sem comandos (apenas one-way push)**
   - Pros: simplicidade.
   - Contras: perde `/daily` force-fire + `/alerts` query.
   - Descartada: UX fraca.

## Consequencias

- **Positivas**: cluster-internal so; sem ingress publico; reconnect
  automatico.
- **Negativas**: bandwidth idle 24/7 (Telegram open connection 25s);
  multi-pod = polluted (cada pod competes getUpdates) — single pod
  V0.1 OK.
- **Neutras**: chat ID whitelist hardcoded em settings — futuro pode
  vir de Vault dinamico.

## Proximas acoes

- Ticket [[NTF-008]] — implementar bot commands (`/status` real check
  18 produtos).
- Ticket [[NTF-011]] — single-active poller via leader election.

## Referencias

- README.md secao "Bot commands"
- `rewire_shared.notify.telegram.TelegramAdapter`

## Historico de revisoes

| Data | Autor | Mudanca |
|---|---|---|
| 2026-05-23 | audit-agent | criacao retroativa |

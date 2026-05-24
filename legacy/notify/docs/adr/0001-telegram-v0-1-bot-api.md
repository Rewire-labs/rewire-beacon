# ADR 0001 — V0.1 dispatcher Telegram Bot API (replace Slack)

- **Status**: Accepted
- **Data**: 2026-05-18
- **Decisores**: Alessandro Queiroz
- **Consulta tecnica**: cluster `docs/futuros_produtos/futuros_produtos.md` §2

## Contexto

Notification interno hoje usa Slack `#cluster-team`. Slack tem custos
crescentes (US$ 7.25/user/mes), API limites, e nao eh OSS. Operador
unico tambem prefere PT-BR mobile-first.

Spec arquitetura define 3 usos:

- **Uso A** — interno (operador + ops team) — alta priori.
- **Uso B** — outbound Gold+ customers — V0.2.
- **Uso C** — outbound webhooks customer — V0.2.

V0.1 cobre apenas Uso A.

## Decisao

Adotar **Telegram Bot API** (`@RewireLabsBot`) como backend V0.1 para
notificacao interna. FastAPI dispatcher fan-out Alertmanager webhook
+ Redpanda `cluster.events.global` topic + APScheduler daily digest
09:00 BRT + long-poll bot commands.

Chats autorizados: Alessandro PV (`1860275106`) + Rewire Labs group
(`-5039808049`). Outros recebem "not authorised".

## Alternativas consideradas

1. **Manter Slack**
   - Pros: status quo, ja conhecido.
   - Contras: custo crescente, nao OSS, sem PT-BR mobile-first.
   - Descartada: feedback memory "OSS sobre SaaS pago".

2. **Discord**
   - Pros: free unlimited, rich UI.
   - Contras: orientado a comunidade, nao ops; UX divergente.
   - Descartada.

3. **Mattermost/Rocket.Chat self-hosted**
   - Pros: OSS, controle total.
   - Contras: 1 servico extra ops; mobile app nao trivial; team de 1
     nao justifica.
   - Descartada: overkill V0.1.

4. **Email puro (Postal)**
   - Pros: simples.
   - Contras: nao real-time, no push mobile, sem inline keyboard.
   - Descartada: latencia.

## Consequencias

- **Positivas**: zero custo (Bot API free); push mobile nativo;
  inline keyboards (Action runbook URLs); PT-BR.
- **Negativas**: dependencia Telegram (BR popular mas sob censura
  potencial em paises); rate limit 30 msg/s.
- **Neutras**: roadmap BEACON V0.2 multi-canal (email/SMS/WA/push).

## Proximas acoes

- Ticket [[NTF-002]] — adapter Telegram.
- Ticket [[NTF-010]] — BEACON V0.2 (multi-canal).

## Referencias

- README.md
- cluster `docs/futuros_produtos/futuros_produtos.md` §2

## Historico de revisoes

| Data | Autor | Mudanca |
|---|---|---|
| 2026-05-23 | audit-agent | criacao retroativa |

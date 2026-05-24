# ADR 0009 — Roadmap BEACON V0.2 multi-canal (email/SMS/WA/push/web push)

- **Status**: Proposed
- **Data**: 2026-05-18
- **Decisores**: Alessandro Queiroz
- **Consulta tecnica**: cluster `docs/futuros_produtos/futuros_produtos.md` §2

## Contexto

V0.1 (atual) cobre apenas Uso A (interno via Telegram). Usos B (outbound
Gold+ customers) e C (outbound webhooks customer) sao requisitos de
2026 Q3 (3-4 meses MVP) — produto comercial BEACON.

Stack target V0.2:

- FastAPI 0.115+ Python 3.13 (ja presente)
- Postal 3.x (email server self-hosted)
- Zenvia/TotalVoice (SMS BR via parceria)
- CONNECT API (WhatsApp Business — produto futuro Rewire)
- APNs/FCM (push mobile)
- VAPID (push web)
- ClickHouse 24.x (event analytics)
- Lago billing integration

Cross-product:
- BEACON usa CONNECT como camada WhatsApp.
- AUDIT TRAIL anchora consents + opt-outs.

Nao-objetivos V0.2: voice calling, fax, email marketing pesado.

## Decisao

Roadmap V0.2 declarado. Implementacao em iteracoes (email primeiro,
SMS segundo, WA terceiro, push mobile/web quarto). Cada canal eh ADR
separada quando implementado.

API unificada `POST /v1/notifications` com `{channel,
recipient, template, vars}`. Substitui multiplas APIs especificas.

## Alternativas consideradas

1. **Twilio/SendGrid SaaS**
   - Pros: managed, sem ops.
   - Contras: feedback memory "OSS sobre SaaS pago"; dolar exchange
     rate; LGPD risk (USA datacenter).
   - Descartada.

2. **Multiplas APIs especificas (/email, /sms, /wa)**
   - Pros: explicit per canal.
   - Contras: cliente tem que conhecer 5 APIs; routing logic em cada
     producer.
   - Descartada.

## Consequencias

- **Positivas**: Single API multi-canal; OSS self-hosted alinhamento
  feedback memory; BR-focus (Zenvia/CONNECT).
- **Negativas**: ops overhead (Postal SMTP, ClickHouse); Authentik
  consent management complexo.
- **Neutras**: V0.1 Telegram continua co-existir como canal "ops
  internal" mesmo apos V0.2.

## Proximas acoes

- Ticket [[NTF-010]] — V0.2 Postal email channel.
- Ticket [[NTF-015]] — V0.2 Zenvia SMS.
- Ticket [[NTF-016]] — V0.2 CONNECT WhatsApp.
- ADRs separadas por canal quando implementadas (`00NN-*-channel.md`).

## Referencias

- README.md secao "Roadmap evolutivo — BEACON"
- cluster `docs/futuros_produtos/futuros_produtos.md` §2

## Historico de revisoes

| Data | Autor | Mudanca |
|---|---|---|
| 2026-05-23 | audit-agent | criacao retroativa |

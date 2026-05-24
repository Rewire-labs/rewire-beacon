# ADR 0006 — Cross-product compatibility: BEACON como notification dispatcher universal

**Status**: Accepted
**Data**: 2026-05-23

## Contexto

Matrix `docs/services/CROSS_PRODUCT_COMPATIBILITY.md` dimensão 8 lista 14+
produtos producers de notif (ASCEND, FOUNDRY, HOST, DEPLOY, CLOUDX,
CITADEL-CLOUD, PULSE-CLOUD, GUARDIAN, DBAAS-BR, PHALANX, AUDIT_TRAIL,
SENTINEL, Customer Support, Watchdog-LLM, etc).

Hoje cada produto reimplementa SMTP/SMS/Telegram. Sem hub central, há:
- duplicação;
- falta de cross-channel unsubscribe;
- falta de audit chain per mensagem;
- falta de anti-spam ML cross-produto.

## Decisão

BEACON é **dispatcher canonical** para email/SMS/WhatsApp/push (mobile + web).
Contratos:

1. **API REST unified**: `POST /beacon/v1/messages` com body
   `{channel, recipient, template_id, params, tenant_id, lawful_basis}`.
2. **Channel router** automático com fallback (email → SMS → WhatsApp
   se primario falha) configurável per template.
3. **Consent cross-channel** — opt-out de email vale para todos os canais
   do mesmo tenant (suppression list unified).
4. **Audit chain CITADEL** per mensagem com lawful_basis tag.
5. **Anti-spam ML** detecta padrão abuso preventivamente.
6. **WhatsApp via CONNECT** layer.
7. **SDK clientes**: Python/Go/TS `rewire-beacon-client`.

## Consequências

- Notif cross-produto sem código duplicado.
- LGPD compliance (consent + opt-out + audit).
- Diferencial: única API BR unified channels.

## Cross-references

- Matrix dimensão 8
- BEACON spec decisões 15-25
- Ticket: `docs/tickets/phase-1-cross-product-compat/xpc-beacon-001-publish-notification-api.md`

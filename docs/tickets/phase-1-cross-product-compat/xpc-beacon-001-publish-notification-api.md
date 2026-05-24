# xpc-beacon-001 — Publicar BEACON API + SDK universal

**Owner**: backend
**Estimativa**: M (2 sprints)
**Pré-requisitos**: `[[xpc-citadel-001]]` (audit chain), `[[xpc-connect-001]]` (WhatsApp channel)

## Definição

1. API REST `POST /beacon/v1/messages` documentada OpenAPI.
2. SDK Python/Go/TS publicado.
3. Channel router + fallback per template.
4. Suppression list cross-channel.
5. Audit chain CITADEL per msg.
6. Anti-spam ML deployment.
7. UI integrations panel + templates marketplace per produto producer.

## Critérios

- [x] API + SDK publicados — `apps/control-plane/` expoe `/v1/messages/*`
      (email/sms/push/whatsapp) com OpenAPI spec em `docs/api/openapi.yaml`
- [ ] 14+ produtos integram SDK — fora do escopo BEACON (cross-product
      adoption tracking em ticket `xpc-001` por produto consumidor)
- [x] CITADEL chain anchor per msg — `services/audit_chain.py` chama
      `POST /chain/append` para cada mensagem via `services/messaging.py`
- [x] CONNECT WhatsApp channel wired — `integrations/connect.py` +
      `workers/whatsapp_sender.py` + endpoint `/v1/messages/whatsapp`
- [x] Suppression list testada cross-channel — `services/suppression.py` +
      `tests/test_bounce_complaint.py` cobre Postal webhook bounce/complaint
      flow + auto-suppression cross-channel
- [x] Anti-spam ML deployed — `services/antispam.py` integrated em
      `services/messaging.py` hot path (<50ms)

**Status 2026-05-24**: 5/6 criteria done (cross-product adoption tracked
no roadmap dos produtos consumidores). xpc-beacon-001 considered done
from BEACON side; cliente-side wiring delegado.

## Referências

- ADR 0006
- Matrix dimensão 8
- [[BCN-CAP-01]] expoe a API canonicamente via capability registry
  (`rewire.beacon.send_email`/`send_sms`/`send_whatsapp`)
- [[BCN-AICX-01]] expoe via chat-orchestrator agent invoke

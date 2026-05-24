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

- [ ] API + SDK publicados
- [ ] 14+ produtos integram SDK
- [ ] CITADEL chain anchor per msg
- [ ] CONNECT WhatsApp channel wired
- [ ] Suppression list testada cross-channel
- [ ] Anti-spam ML deployed

## Referências

- ADR 0006
- Matrix dimensão 8

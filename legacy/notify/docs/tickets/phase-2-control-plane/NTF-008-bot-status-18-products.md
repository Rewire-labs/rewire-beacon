# NTF-008 — `/status` real check 18 produtos

- **Owner**: @alessandro
- **Estimativa**: M
- **Pre-reqs**: 18 produtos com `/healthz` ou `/readyz`
- **Status**: [ ] open (`/status` stubbed V0.1)

## Definicao

Bot command `/status` checa health de 18 produtos Rewire:
12 legacy (PROFITOR, etc) + 6 novos (CITADEL-CLOUD, PULSE-CLOUD,
DBAAS-BR, CLOUDX, AUDIT_TRAIL, HOST).

Response: tabela emoji per produto (✅ ✗ ⚠ ❓).

## Aceite

- [ ] Concurrent httpx checks (timeout 3s per produto).
- [ ] Settings env var `REWIRE_NOTIFY_PRODUCTS_HEALTH_URLS` JSON map.
- [ ] Format response Telegram-friendly (max 4096 chars).
- [ ] Cache 60s para reduzir spam.
- [ ] Pytest cobertura.

## Refs

- [ADR 0006](../../adr/0006-bot-command-poller-long-poll.md)
- README.md secao "Bot commands"

## Notas

Usuario reference em memory: 18 produtos = 12 legacy + 6 novos.

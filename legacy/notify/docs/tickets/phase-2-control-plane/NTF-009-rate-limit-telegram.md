# NTF-009 — Rate limit Telegram 30 msg/s + circuit breaker

- **Owner**: @alessandro
- **Estimativa**: S
- **Pre-reqs**: [[NTF-002]]
- **Status**: [ ] open

## Definicao

Telegram Bot API tem rate limit 30 msg/s globally + 1 msg/s per chat.
Quando estouramos (alert storm), Telegram retorna 429. Implementar
token bucket + circuit breaker.

## Aceite

- [ ] Token bucket global 30/s.
- [ ] Per-chat 1/s.
- [ ] 429 backoff (`Retry-After` header).
- [ ] Circuit breaker: 10 falhas seguidas = pause 60s.
- [ ] Buffer in-memory pending msgs (max 1000).
- [ ] Pytest com slot bucket simulation.

## Refs

- [ADR 0001](../../adr/0001-telegram-v0-1-bot-api.md)
- `rewire_shared.notify.telegram.TelegramAdapter`

## Notas

Alert storm = N pods crashloop simultaneo = 100s alerts em segundos.

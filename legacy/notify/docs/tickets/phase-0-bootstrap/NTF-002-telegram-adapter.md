# NTF-002 — Telegram adapter `rewire_shared.notify.telegram`

- **Owner**: @alessandro
- **Estimativa**: M
- **Pre-reqs**: rewire_shared lib path
- **Status**: [x] done

## Definicao

Adapter Telegram em `libs/rewire_shared/python/rewire_shared/notify/telegram/`:

- `events.py` — `EventKind`, `Severity`, `AlertEvent` types.
- `formatter.py` — registry kind→template (12 kinds).
- `adapter.py` — `TelegramAdapter` (send, getUpdates, inline keyboard).

Reusable from outros produtos.

## Aceite

- [x] 12 kinds EventKind enum.
- [x] Formatter registry com PT-BR template + emoji per kind.
- [x] Adapter send com inline keyboard support.
- [x] Pytest mock httpx (rewire_shared/python/tests/notify/telegram/).

## Refs

- [ADR 0002](../../adr/0002-12-event-kinds-canonical.md)
- `libs/rewire_shared/python/rewire_shared/notify/telegram/`

## Notas

Shared lib — outros produtos podem importar.

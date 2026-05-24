# NTF-001 — Scaffold FastAPI app + dispatcher

- **Owner**: @alessandro
- **Estimativa**: M
- **Pre-reqs**: pyproject
- **Status**: [x] done

## Definicao

Scaffold `src/rewire_notify/` FastAPI app: `api.py` (routes), `main.py`
(boot + lifespan + dispatcher init), `dispatcher.py` (Alertmanager
parser + EventKind translation), `settings.py` (Pydantic-Settings).

## Aceite

- [x] Boot via `uvicorn rewire_notify.main:app`.
- [x] Routes `/healthz`, `/readyz`, `/alerts/telegram`, `/events`.
- [x] `app.state.dispatcher` exposto para handlers.
- [x] Pytest base passing.

## Refs

- [ADR 0001](../../adr/0001-telegram-v0-1-bot-api.md)
- `src/rewire_notify/main.py`

## Notas

CORS aberto V0.1 (cluster-internal). Apertar em prod via NetworkPolicy.

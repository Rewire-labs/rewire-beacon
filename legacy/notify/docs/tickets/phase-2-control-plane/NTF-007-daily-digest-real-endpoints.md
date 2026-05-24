# NTF-007 — Daily digest real endpoints Lago/Foundry/Alertmanager

- **Owner**: @alessandro
- **Estimativa**: M
- **Pre-reqs**: Lago/Foundry/Alertmanager UP
- **Status**: [ ] open (`daily_digest.py` scaffolded com stubs)

## Definicao

`run_daily_digest` consulta endpoints reais e formata digest:

- Lago `/api/v1/events?from=24h&to=now` — total emit billing events.
- Foundry `/api/v1/prs?merged=true&since=24h` — PRs mergeados.
- Alertmanager `/api/v2/alerts` — open alerts count + breakdown.
- (Futuro) Asaas `/payments?status=received&since=24h`.
- (Futuro) HOST `/v1/vms?provisioned=true&since=24h`.

## Aceite

- [ ] httpx async client com timeout 10s per call.
- [ ] Falha de 1 endpoint nao quebra digest (graceful degradation).
- [ ] Template `daily.summary` formatado em formatter.
- [ ] Pytest com respx mocks.
- [ ] Settings env vars per endpoint (URL + auth).

## Refs

- [ADR 0005](../../adr/0005-daily-digest-apscheduler.md)
- `src/rewire_notify/daily_digest.py`

## Notas

JWT internal token via `Settings.foundry_internal_jwt`.

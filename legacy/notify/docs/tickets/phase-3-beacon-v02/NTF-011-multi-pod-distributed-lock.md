# NTF-011 — Multi-pod distributed lock APScheduler+poller

- **Owner**: @alessandro
- **Estimativa**: M
- **Pre-reqs**: Redis UP
- **Status**: [ ] open

## Definicao

V0.1 eh single-pod (APScheduler + bot poller). Multi-pod (HA) requer
leader election ou distributed lock para evitar duplicate daily
digest + duplicate getUpdates contention.

Implementar Redis lock (Redlock pattern) com TTL 60s renovado.

## Aceite

- [ ] Redis lock `rewire-notify:leader` com TTL.
- [ ] Active pod renova; passive sleep.
- [ ] APScheduler + poller so executam se holder.
- [ ] Pytest cobertura.

## Refs

- [ADR 0005](../../adr/0005-daily-digest-apscheduler.md)
- [ADR 0006](../../adr/0006-bot-command-poller-long-poll.md)

## Notas

V0.1 OK single-pod. V0.2 com mais traffic requer HA.

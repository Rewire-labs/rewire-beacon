# NTF-018 — VAPID push web

- **Owner**: @alessandro
- **Estimativa**: M
- **Pre-reqs**: [[NTF-010]]
- **Status**: [ ] open (V0.2+)

## Definicao

Canal web push via VAPID + Service Worker no installer/vector-ui/admin
frontends. Subscription registrada via browser Notification API.

## Aceite

- [ ] VAPIDAdapter (pywebpush ou similar).
- [ ] Subscription registry table.
- [ ] Service Worker template em frontends Rewire.
- [ ] Pytest cobertura.

## Refs

- [ADR 0009](../../adr/0009-beacon-v0-2-multi-canal-roadmap.md)

## Notas

Util para admins logados em browser receberem alerts criticos sem
mobile app.

# NTF-017 — APNs/FCM push mobile

- **Owner**: @alessandro + mobile app team
- **Estimativa**: L
- **Pre-reqs**: [[NTF-010]], mobile app SDK
- **Status**: [ ] open (V0.2+)

## Definicao

Canal push mobile via Apple APNs (iOS) + Firebase Cloud Messaging
(Android). Device tokens registrados via mobile SDK no signup.

## Aceite

- [ ] APNsAdapter (HTTP/2 JWT auth).
- [ ] FCMAdapter (HTTP v1 OAuth2).
- [ ] Device token registry `notify_devices` table.
- [ ] Silent push para data refresh.
- [ ] Badge count management.
- [ ] Pytest mocks.

## Refs

- [ADR 0009](../../adr/0009-beacon-v0-2-multi-canal-roadmap.md)

## Notas

Mobile apps Rewire ainda nao existem produtivamente — V0.2+ low priority.

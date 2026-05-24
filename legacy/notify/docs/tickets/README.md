# Tickets — rewire-notify (BEACON futuro)

Backlog estruturado por fase. Prefixo `NTF-`.

## Convencoes

- Formato: `# NTF-NNN — titulo / Owner / Estimativa S/M/L/XL / Pre-reqs / Definicao / Aceite / Refs / Notas`.
- Cross-refs `[[NTF-NNN]]`.
- ADRs: `[ADR NNNN](../adr/NNNN-*.md)`.
- Status: `[ ]` open, `[~]` in progress, `[x]` done, `[/]` blocked.
- Owner default: `@alessandro`.

## Phase 0 — Bootstrap V0.1

- [x] [NTF-001](phase-0-bootstrap/NTF-001-scaffold-fastapi-app.md) — Scaffold FastAPI app + dispatcher
- [x] [NTF-002](phase-0-bootstrap/NTF-002-telegram-adapter.md) — Telegram adapter `rewire_shared.notify.telegram`

## Phase 1 — Foundation dispatch + events

- [x] [NTF-003](phase-1-foundation/NTF-003-alertmanager-webhook-intake.md) — `/alerts/telegram` HMAC + parser
- [ ] [NTF-004](phase-1-foundation/NTF-004-kafka-consumer-cluster-events.md) — Kafka consumer `cluster.events.global`
- [ ] [NTF-005](phase-1-foundation/NTF-005-producer-events-cross-product.md) — Producer events canonicos cross-product
- [ ] [NTF-006](phase-1-foundation/NTF-006-alertmanager-helm-config.md) — Doc Alertmanager helm config + HMAC

## Phase 2 — Control-plane completeness V0.1

- [ ] [NTF-007](phase-2-control-plane/NTF-007-daily-digest-real-endpoints.md) — Daily digest real endpoints Lago/Foundry/Alertmanager
- [ ] [NTF-008](phase-2-control-plane/NTF-008-bot-status-18-products.md) — `/status` real check 18 produtos
- [ ] [NTF-009](phase-2-control-plane/NTF-009-rate-limit-telegram.md) — Rate limit Telegram 30 msg/s + circuit breaker

## Phase 3 — Roadmap BEACON V0.2

- [ ] [NTF-010](phase-3-beacon-v02/NTF-010-postal-email-channel.md) — Postal email channel
- [ ] [NTF-011](phase-3-beacon-v02/NTF-011-multi-pod-distributed-lock.md) — Multi-pod distributed lock APScheduler+poller
- [ ] [NTF-012](phase-3-beacon-v02/NTF-012-clickhouse-event-analytics.md) — ClickHouse 24.x event analytics
- [ ] [NTF-013](phase-3-beacon-v02/NTF-013-authentik-consent-management.md) — Authentik consent management opt-outs

## Phase 4 — Deploy + cluster integration

- [x] [NTF-014](phase-4-deploy/NTF-014-helm-chart-observability.md) — Helm chart prod values (observability namespace, wave 5)
- [ ] [NTF-015](phase-3-beacon-v02/NTF-015-zenvia-sms-channel.md) — Zenvia SMS channel (BR)
- [ ] [NTF-016](phase-3-beacon-v02/NTF-016-connect-whatsapp-channel.md) — CONNECT WhatsApp channel (cross-product)
- [ ] [NTF-017](phase-4-deploy/NTF-017-apns-fcm-push-mobile.md) — APNs/FCM push mobile
- [ ] [NTF-018](phase-4-deploy/NTF-018-vapid-push-web.md) — VAPID push web
- [ ] [NTF-019](phase-4-deploy/NTF-019-lago-billing-integration.md) — Lago billing integration (per-notification metering)

## Phase 5 — Compliance + cross-product

- [ ] [NTF-020](phase-5-compliance/NTF-020-audit-trail-anchor-consents.md) — AUDIT TRAIL anchor consents + opt-outs
- [ ] [NTF-021](phase-5-compliance/NTF-021-lgpd-dsar-flow.md) — LGPD DSAR data export flow
- [ ] [NTF-022](phase-5-compliance/NTF-022-prometheus-exporter.md) — Prometheus exporter (delivery rate, bounce, click metrics)
- [ ] [NTF-023](phase-5-compliance/NTF-023-template-bilingue.md) — Templates bilingue PT-BR + EN-US

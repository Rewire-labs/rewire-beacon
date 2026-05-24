# rewire-notify (BEACON futuro)

Internal notification dispatcher for the Rewire platform — V0.1 backend
is the official Telegram Bot API (`@RewireLabsBot`). Replaces the
legacy Slack `#cluster-team` channel (uso A from the architecture
spec). Customer Gold+ outbound (uso B) and customer outbound webhooks
(uso C) live in `rewire_shared.webhook_tools` and a future V0.2 module.

## Roadmap evolutivo — BEACON

V0.1 (atual): Telegram dispatcher interno (`@RewireLabsBot`).

V0.2 (Q3 2026, 3-4 meses MVP): evolução para **BEACON** — Notification
Platform multi-canal BR (email + SMS + WhatsApp + push mobile + push web)
em uma única API. Spec completa em
[docs/futuros_produtos/futuros_produtos.md §2](https://github.com/Rewire-labs/cluster/blob/main/docs/futuros_produtos/futuros_produtos.md).

Stack target V0.2:
- FastAPI 0.115+ Python 3.13 (já presente)
- Postal 3.x (email server self-hosted)
- Zenvia/TotalVoice (SMS BR via parceria)
- CONNECT API (WhatsApp Business — produto futuro)
- APNs/FCM (push mobile)
- VAPID (push web)
- ClickHouse 24.x (event analytics)
- Lago billing integration

Cross-product:
- BEACON usa CONNECT como camada WhatsApp
- AUDIT TRAIL anchora consents + opt-outs

Não-objetivos V0: voice calling, fax, email marketing pesado.

## Architecture

```
Alertmanager ─── webhook ──────┐
                                ▼
         /alerts/telegram ─► Dispatcher ─► TelegramAdapter ─► api.telegram.org
Redpanda ─── cluster.events.global ─► KafkaConsumer ────┘
                                ▼
         /events ───────────────┘
                                ▲
APScheduler 09:00 BRT ─► run_daily_digest
                                ▲
TelegramAdapter.getUpdates ─► BotCommandPoller (/status, /daily, /alerts, /help)
```

## Endpoints

| Path                  | Method | Purpose                                  |
|-----------------------|--------|------------------------------------------|
| `/alerts/telegram`    | POST   | Alertmanager webhook intake (HMAC).      |
| `/events`             | POST   | Direct event POST (used by producers without Redpanda). |
| `/healthz`            | GET    | Liveness probe.                          |
| `/readyz`             | GET    | Readiness probe.                         |
| `/metrics`            | GET    | Prometheus exposition.                   |

## 12 supported event kinds

See `rewire_shared.notify.telegram.events.EventKind` and the formatter
registry in `rewire_shared.notify.telegram.formatter`:

| kind                       | severity | inline keyboard |
|----------------------------|----------|-----------------|
| `tenant.onboarded`         | info     | —               |
| `asaas.payment_received`   | info     | —               |
| `product.crashloop`        | critical | —               |
| `vault.sealed`             | critical | View Unseal Runbook |
| `breach.detected`          | critical | View Workflow   |
| `tenant.hard_cap_exceeded` | warn     | Notify Customer / Increase Cap |
| `lgpd.dsar.requested`      | warn     | —               |
| `foundry.pr.merged`        | info     | —               |
| `daily.summary`            | info     | —               |
| `smoke.test.failed`        | critical | —               |
| `cost.anomaly`             | warn     | —               |
| `pricing.change.applied`   | warn     | —               |

## Bot commands

The microservice runs a long-poll loop calling `getUpdates`. Allowed
chats: Alessandro's PV (`1860275106`) and the `Rewire Labs` group
(`-5039808049`). Any other chat receives a polite "not authorised"
reply.

| Command          | Effect                                         |
|------------------|------------------------------------------------|
| `/status`        | Health checks of 18 products (V0.1 stubbed).   |
| `/daily`         | Force-fire the daily digest immediately.       |
| `/alerts`        | List currently-open Alertmanager alerts.       |
| `/help`          | List available commands.                       |

## Routing rules

- `critical` events fan out to BOTH the operator's private chat AND
  the `Rewire Labs` group (private gets push priority).
- `warn` / `info` events go to the group only, silent (no sound).
- `vault.sealed`, `breach.detected`, `product.crashloop`,
  `smoke.test.failed` always escalate to both chats regardless of
  the severity field (defensive override).

## Configuration

All settings live in `rewire_notify.settings.Settings` and read from
env-vars prefixed with `REWIRE_NOTIFY_`. Production overrides come
from the ExternalSecret `rewire-notify-telegram` (Vault paths
`kv/rewire/notify/telegram-{bot-token,chat-id-private,chat-id-group}`).

## Deployment

Deployed via the `argocd/applicationsets/observability.yaml`
ApplicationSet (wave 5) into the `observability` namespace. The Helm
chart sits at `deploy/helm/rewire-notify/`; a standalone
`Application` manifest is available at `deploy/argocd/application.yaml`
for ad-hoc syncs.

## Testing

```bash
cd services/rewire-notify
pip install -e ".[dev]"
pytest tests/

# Optional: send 1 real message to your private chat
INTEGRATION_TEST_TELEGRAM=1 \
  TELEGRAM_BOT_TOKEN=... \
  TELEGRAM_PRIVATE_CHAT_ID=... \
  pytest ../rewire_shared/python/tests/notify/telegram/test_adapter.py::test_integration_send_real_message
```

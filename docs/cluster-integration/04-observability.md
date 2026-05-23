# Cluster integration — Observability

## Metrics

`/metrics` endpoint exposes Prometheus format. Scraped via ServiceMonitor
(production) + PodMonitor (workers).

Key metrics emitted:

- `beacon_requests_total{method,path,status}` (FastAPI default)
- `beacon_request_duration_seconds_bucket{...}` (histogram)
- `beacon_kafka_publish_failures_total` (custom — best-effort)
- `beacon_antispam_decisions_total{decision}` (custom — TBD)
- `beacon_audit_chain_anchored_total{success}` (custom — TBD)

## Logs

structlog JSON to stdout. Aggregated via PULSE-CLOUD Loki via Promtail
DaemonSet.

Canonical fields:
- `event`: action name (e.g. `email_sender.handle_failed`)
- `organization_id`, `message_id`, `channel`, `error`

## Traces

OTLP exporter to PULSE-CLOUD OTEL collector via env vars:

```
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.pulse-cloud.svc:4317
OTEL_SERVICE_NAME=rewire-beacon
```

FastAPI auto-instrumentation enabled via `opentelemetry-instrumentation-fastapi`.

## Dashboards Grafana

Importar JSONs em `cluster/grafana-dashboards/`:
- `beacon-overview.json` — req/s + p50/p95/p99 latency
- `beacon-channels.json` — sent/delivered/bounced/complained por canal
- `beacon-deliverability.json` — reputation score + bounce rate por IP

## Alertas (PrometheusRule)

- `BeaconControlPlaneDown` — `up{job="beacon-control-plane"} == 0` for 2m
- `BeaconHighBounceRate` — bounce rate > 5% por 30min em qualquer org
- `BeaconKafkaLag` — consumer group lag > 10k mensagens
- `BeaconAntiSpamBlockSpike` — `rate(beacon_antispam_decisions_total{decision="block"}[5m]) > 10`

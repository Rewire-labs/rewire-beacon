# NTF-022 — Prometheus exporter (delivery rate, bounce, click metrics)

- **Owner**: @alessandro
- **Estimativa**: S
- **Pre-reqs**: [[NTF-012]]
- **Status**: [ ] open

## Definicao

Metricas custom:

- `notify_dispatched_total{kind=,channel=,severity=}` counter.
- `notify_delivery_success_total{channel=}` counter.
- `notify_delivery_failure_total{channel=,reason=}` counter.
- `notify_bounce_total{channel=}` counter.
- `notify_click_total{channel=}` counter.
- `notify_opt_out_total{channel=}` counter.
- `notify_latency_seconds{channel=}` histogram.

## Aceite

- [ ] `prometheus_client` instrumentation.
- [ ] `/metrics` endpoint registered.
- [ ] ServiceMonitor em Helm chart.
- [ ] Grafana dashboards JSON em `deploy/helm/rewire-notify/grafana/`.

## Refs

- README.md secao "Endpoints" (`/metrics`)
- cluster ADR 0061 (Prometheus)

## Notas

PULSE-CLOUD dashboards reuse.

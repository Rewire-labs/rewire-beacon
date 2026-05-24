"""rewire-notify — internal notification dispatcher microservice.

V0.1 backends:
    Telegram Bot API (``@RewireLabsBot``) for operator + Rewire Labs
    group. Replaces the legacy Slack ``#cluster-team`` channel.

Endpoints:
    POST /alerts/telegram       — Alertmanager webhook intake.
    POST /events                — Redpanda consumer dispatch (12 kinds).
    GET  /healthz / /readyz      — k8s probes.
    GET  /metrics                — Prometheus exposition.

Background tasks running inside the FastAPI lifespan:
    - Bot command long-poller (``/status``, ``/daily``, ``/alerts``,
      ``/help``).
    - Redpanda consumer task (``cluster.events.global`` → telegram).
    - APScheduler cron job at 09:00 BRT firing the daily digest.
"""

__version__ = "0.1.0"

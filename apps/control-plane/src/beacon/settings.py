"""BEACON canonical settings — Pydantic Settings.

Canonical env var prefix: MESSAGING_* (aligned with Helm chart + ExternalSecrets).
All MESSAGING_* env vars injected by Helm ExternalSecrets (kv/rewire-messaging/*)
are read without the prefix stripped — pydantic strips the prefix automatically.

V0 defaults allow local dev without external services; in-cluster the Helm
ExternalSecret populates the secrets.

NOTE: Previously the prefix was BEACON_* which was mismatched from Helm
(RW-MESSAGING-01 fix).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for BEACON control-plane."""

    model_config = SettingsConfigDict(
        env_prefix="MESSAGING_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -- service identity -------------------------------------------------
    service_name: str = "rewire-messaging"
    service_version: str = "0.1.0"
    environment: str = Field(default="dev", description="dev | staging | prod")
    log_level: str = "INFO"

    # -- HTTP -------------------------------------------------------------
    http_host: str = "0.0.0.0"  # noqa: S104 — container-bound
    http_port: int = 8080

    # -- Persistence (V0 stubs — SQLite fallback se nao providenciado) ----
    database_url: str = "sqlite+aiosqlite:///./beacon.dev.db"
    redis_url: str = "redis://localhost:6379/0"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/%2F"
    kafka_brokers: str = "localhost:9092"
    clickhouse_url: str = "http://localhost:8123"

    # -- Identity / security ---------------------------------------------
    vault_addr: str = "http://vault.security.svc.cluster.local:8200"
    oidc_issuer: str = "https://auth.rewirelabs.dev/application/o/messaging/"
    oidc_client_id: str = "messaging"
    oidc_client_secret: str = "dev-only-not-prod"  # noqa: S105 — dev fallback
    # JWKS endpoint for RS256 signature validation (ADR0046). Empty default ->
    # derived from oidc_issuer via well-known discovery suffix.
    oidc_jwks_uri: str = ""
    # Expected `aud` claim for UI/SDK tokens (Authentik client_id by default).
    oidc_audience: str = "messaging"
    # Dev/test ONLY: shared HS256 secret to accept symmetric tokens without a
    # live Authentik/JWKS. MUST be empty in prod (ExternalSecret never sets it).
    oidc_dev_hs256_secret: str = ""

    # -- Inter-agent (INTER_AGENT_COMM_SPEC §1.2) -------------------------
    agent_audience: str = "agents.rewire.svc"
    agent_jwks_uri: str = ""
    # Dev/test ONLY: when true, /agent/v1/invoke accepts header-only identity
    # (no verified JWT). MUST be false in prod — the header-trust path was the
    # RW-MESSAGING-07 auth bypass.
    agent_invoke_dev_allow_unsigned: bool = False

    # -- Cross-product ----------------------------------------------------
    connect_internal_base_url: str = "http://connect.connect.svc.cluster.local:8080"
    citadel_chain_base_url: str = "http://citadel.rewire-citadel.svc.cluster.local:8080"
    audit_trail_base_url: str = "http://audit-trail.rewire-audit-trail.svc.cluster.local:8080"

    # -- Channels (V0 placeholders — workers nao implementados) -----------
    postal_api_url: str = "http://postal.beacon.svc.cluster.local:5000"
    postal_api_key: str = ""
    ses_region: str = "sa-east-1"
    ses_access_key_id: str = ""
    ses_secret_access_key: str = ""
    zenvia_api_token: str = ""
    totalvoice_api_token: str = ""
    # Resend fallback (Postal -> Resend on 5xx). Populated via ExternalSecret
    # from kv/rewire-messaging/resend-api-key. Empty default = fallback disabled.
    resend_api_key: str = ""
    apns_team_id: str = ""
    apns_key_id: str = ""
    fcm_service_account_json: str = ""
    vapid_public_key: str = ""
    vapid_private_key: str = ""

    # -- Observability ----------------------------------------------------
    otel_exporter_otlp_endpoint: str = (
        "http://otel-collector.observability.svc.cluster.local:4317"
    )
    otel_service_name: str = "rewire-messaging"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor — instantiated once per process."""
    return Settings()

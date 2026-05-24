"""Configuration via environment variables / Vault-mounted secrets."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for rewire-notify.

    Loaded primarily from environment variables (which Kubernetes
    populates from the ``rewire-notify-telegram`` Secret). Defaults
    here mirror the architecture spec and are safe for local dev.
    """

    model_config = SettingsConfigDict(
        env_prefix="REWIRE_NOTIFY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- Telegram ---------------------------------------------------- #
    bot_token: str = Field(default="", description="Telegram bot token (Vault).")
    chat_id_private: str = Field(default="1860275106", description="Alessandro PV.")
    chat_id_group: str = Field(default="-5039808049", description="Rewire Labs group.")

    # ---- HTTP server ------------------------------------------------- #
    http_host: str = Field(default="0.0.0.0")  # noqa: S104 — k8s service
    http_port: int = Field(default=8080)

    # ---- Alertmanager webhook auth ----------------------------------- #
    alertmanager_hmac_secret: str = Field(default="")

    # ---- Redpanda consumer ------------------------------------------- #
    kafka_brokers: str = Field(default="redpanda.kafka:9092")
    kafka_topic_events: str = Field(default="cluster.events.global")
    kafka_consumer_group: str = Field(default="rewire-notify-v1")
    enable_kafka_consumer: bool = Field(default=True)

    # ---- Bot command poller ----------------------------------------- #
    enable_bot_poller: bool = Field(default=True)
    bot_poll_timeout_seconds: int = Field(default=25)

    # ---- Daily digest cron ------------------------------------------ #
    enable_daily_digest: bool = Field(default=True)
    daily_digest_cron_hour_brt: int = Field(default=9)
    daily_digest_cron_minute_brt: int = Field(default=0)

    # ---- Service endpoints used by the digest aggregator ----------- #
    lago_api_url: str = Field(default="http://lago-api.lago.svc.cluster.local:3000")
    lago_api_key: str = Field(default="")
    foundry_api_url: str = Field(
        default="http://foundry-cp.foundry.svc.cluster.local:8080"
    )
    foundry_internal_jwt: str = Field(default="")

    # ---- Observability ---------------------------------------------- #
    service_name: str = Field(default="rewire-notify")
    environment: str = Field(default="production")
    log_level: str = Field(default="INFO")


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the process-wide :class:`Settings` singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

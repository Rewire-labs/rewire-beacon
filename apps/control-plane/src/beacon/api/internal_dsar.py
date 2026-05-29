"""``/internal/v1/dsar/*`` — AUDIT orchestrator-facing DSAR endpoints (rewire-messaging).

GAP CLOSURE 2 (2026-05-25). Canonical /internal/v1/dsar/{tenant_id}/{op}
shape expected by AUDIT orchestrator fanout. HMAC-verified, internal-only.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter

from rewire_shared.lgpd_dsar import (
    DSARDeleterContext,
    DSARDeleteOutcome,
    DSARExportArtifact,
    DSARExporterContext,
    SubjectDataDeleter,
    SubjectDataExporter,
    create_dsar_router,
)

logger = logging.getLogger(__name__)


_async_sessionmaker: Any = None


def _get_sessionmaker() -> Any:
    global _async_sessionmaker
    if _async_sessionmaker is None:
        try:
            from sqlalchemy.ext.asyncio import (
                async_sessionmaker,
                create_async_engine,
            )

            from beacon.settings import get_settings

            engine = create_async_engine(get_settings().database_url, echo=False)
            _async_sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
        except Exception as exc:  # noqa: BLE001
            logger.warning("messaging_dsar.sessionmaker_failed", extra={"err": str(exc)})
            _async_sessionmaker = False
    return _async_sessionmaker or None


class MessagingTenantDataExporter(SubjectDataExporter):
    supported_ops = frozenset({"export"})

    async def export(self, ctx: DSARExporterContext) -> DSARExportArtifact:
        sm = _get_sessionmaker()
        tenant_id = ctx.request.tenant_id
        subject_email = ctx.request.subject_email
        counts: dict[str, int] = {}
        payload: dict[str, Any] = {
            "product": "rewire-messaging",
            "tenant_id": tenant_id,
            "subject_email": subject_email,
            "tables": {},
        }

        if sm is None:
            return DSARExportArtifact(record_counts={}, payload=None)

        try:
            from sqlalchemy import text  # noqa: PLC0415

            async with sm() as session:
                for table, query in _DSAR_QUERIES:
                    try:
                        rows = (
                            await session.execute(
                                text(query),
                                {"tenant_id": tenant_id, "subject_email": subject_email},
                            )
                        ).mappings().all()
                        if rows:
                            counts[table] = len(rows)
                            payload["tables"][table] = [dict(r) for r in rows[:200]]
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(
                            "lgpd_dsar.messaging.export.table_failed",
                            extra={"table": table, "tenant_id": tenant_id, "err": str(exc)},
                        )
        except Exception as exc:  # noqa: BLE001
            logger.warning("lgpd_dsar.messaging.export.session_failed", extra={"err": str(exc)})

        return DSARExportArtifact(
            record_counts=counts,
            payload=payload if counts else None,
        )


_DSAR_QUERIES: tuple[tuple[str, str], ...] = (
    (
        "notifications",
        """
        SELECT id, channel, status, sent_at
        FROM messaging.notifications
        WHERE organization_id::text = :tenant_id
          AND recipient_email = :subject_email
        ORDER BY 1 DESC
        LIMIT 200
        """,
    ),
    (
        "templates",
        """
        SELECT id, name, channel, created_at
        FROM messaging.templates
        WHERE organization_id::text = :tenant_id
          AND owner_email = :subject_email
        ORDER BY 1 DESC
        LIMIT 200
        """,
    ),
    (
        "delivery_log",
        """
        SELECT id, notification_id, status, occurred_at
        FROM messaging.delivery_log
        WHERE organization_id::text = :tenant_id
          AND recipient_email = :subject_email
        ORDER BY 1 DESC
        LIMIT 200
        """,
    ),
)


class MessagingTenantDataDeleter(SubjectDataDeleter):
    supported_ops = frozenset({"delete", "anonymization"})

    async def delete(self, ctx: DSARDeleterContext) -> DSARDeleteOutcome:
        sm = _get_sessionmaker()
        tenant_id = ctx.request.tenant_id
        subject_email = ctx.request.subject_email
        tombstoned: dict[str, int] = {}
        retained: dict[str, int] = {}
        notes: list[str] = []

        if sm is None:
            return DSARDeleteOutcome(
                deleted={}, tombstoned={}, retained_under_legal_basis={},
                grace_period_seconds=self.grace_period_seconds, notes="db unavailable",
            )

        try:
            from sqlalchemy import text  # noqa: PLC0415

            async with sm() as session:
                for table, sql in _SOFT_DELETE_SQL:
                    try:
                        res = await session.execute(
                            text(sql),
                            {"tenant_id": tenant_id, "subject_email": subject_email},
                        )
                        rows = res.fetchall() if res.returns_rows else []
                        tombstoned[table] = len(rows) if rows else (res.rowcount or 0)
                        await session.commit()
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(
                            "lgpd_dsar.messaging.delete.soft_delete_failed",
                            extra={"table": table, "tenant_id": tenant_id, "err": str(exc)},
                        )
                        await session.rollback()
                        notes.append(f"{table} soft-delete skipped: {exc}")

                for table, sql in _RETAINED_SQL:
                    try:
                        res = await session.execute(
                            text(sql),
                            {"tenant_id": tenant_id, "subject_email": subject_email},
                        )
                        rows = res.fetchall() if res.returns_rows else []
                        retained[table] = len(rows) if rows else (res.rowcount or 0)
                        await session.commit()
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(
                            "lgpd_dsar.messaging.delete.retained_failed",
                            extra={"table": table, "tenant_id": tenant_id, "err": str(exc)},
                        )
                        await session.rollback()
                        notes.append(f"{table} retained-redact skipped: {exc}")
        except Exception as exc:  # noqa: BLE001
            logger.warning("lgpd_dsar.messaging.delete.session_failed", extra={"err": str(exc)})

        return DSARDeleteOutcome(
            deleted={}, tombstoned=tombstoned, retained_under_legal_basis=retained,
            grace_period_seconds=self.grace_period_seconds,
            notes="; ".join(notes) if notes else None,
        )


_SOFT_DELETE_SQL: tuple[tuple[str, str], ...] = (
    (
        "templates",
        """
        UPDATE messaging.templates
        SET tombstoned_at = now(), tombstone_reason = 'lgpd_dsar_delete'
        WHERE organization_id::text = :tenant_id
          AND owner_email = :subject_email
          AND tombstoned_at IS NULL
        RETURNING id
        """,
    ),
)


_RETAINED_SQL: tuple[tuple[str, str], ...] = (
    (
        "delivery_log",
        """
        UPDATE messaging.delivery_log
        SET recipient_email = concat('redacted-', id::text, '@deleted.invalid'),
            pii_redacted = true
        WHERE organization_id::text = :tenant_id
          AND recipient_email = :subject_email
          AND pii_redacted IS DISTINCT FROM true
        RETURNING id
        """,
    ),
    (
        "notifications",
        """
        UPDATE messaging.notifications
        SET recipient_email = concat('redacted-', id::text, '@deleted.invalid'),
            pii_redacted = true
        WHERE organization_id::text = :tenant_id
          AND recipient_email = :subject_email
          AND pii_redacted IS DISTINCT FROM true
        RETURNING id
        """,
    ),
)


def _audit_token_secrets() -> dict[str, str]:
    secrets: dict[str, str] = {}
    current = os.environ.get("AUDIT_TOKEN_HMAC_SECRET")
    previous = os.environ.get("AUDIT_TOKEN_HMAC_SECRET_PREVIOUS")
    if current:
        secrets["current"] = current
    if previous:
        secrets["previous"] = previous
    return secrets


def build_dsar_router() -> APIRouter:
    return create_dsar_router(
        product_slug="rewire-messaging",
        exporter=MessagingTenantDataExporter(),
        deleter=MessagingTenantDataDeleter(),
        shared_secrets_provider=_audit_token_secrets,
    )


router = build_dsar_router()


__all__ = [
    "MessagingTenantDataDeleter",
    "MessagingTenantDataExporter",
    "build_dsar_router",
    "router",
]

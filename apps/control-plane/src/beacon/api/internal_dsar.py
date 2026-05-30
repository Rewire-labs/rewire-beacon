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


def _session_ctx() -> Any:
    """Return the canonical worker (BYPASSRLS) session context.

    DSAR is internal + cross-tenant by design — the AUDIT orchestrator asks
    rewire-messaging for ONE subject's data scoped by an explicit
    ``tenant_id``/``subject_email`` WHERE clause. We use ``worker_session``
    (the same engine/role as the rest of the service, RW-MESSAGING-01) rather
    than spinning up a private sqlite engine. Returns ``None`` when the DB
    layer is unavailable so handlers degrade to an honest empty result.
    """
    try:
        from beacon.db.session import worker_session

        return worker_session
    except Exception as exc:  # noqa: BLE001
        logger.warning("messaging_dsar.session_unavailable", extra={"err": str(exc)})
        return None


class MessagingTenantDataExporter(SubjectDataExporter):
    supported_ops = frozenset({"export"})

    async def export(self, ctx: DSARExporterContext) -> DSARExportArtifact:
        sm = _session_ctx()
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


# Queries against the REAL schema (beacon.*). The subject is identified by the
# notification ``recipient`` (email/phone); deliveries are scoped via their
# parent notification. ``tenant_id`` matches ``beacon.notifications.tenant_id``.
_DSAR_QUERIES: tuple[tuple[str, str], ...] = (
    (
        "notifications",
        """
        SELECT id, channel_kind, consent_basis, created_at
        FROM beacon.notifications
        WHERE tenant_id = :tenant_id
          AND recipient = :subject_email
        ORDER BY created_at DESC
        LIMIT 200
        """,
    ),
    (
        "deliveries",
        """
        SELECT d.id, d.notification_id, d.provider, d.status, d.created_at
        FROM beacon.deliveries d
        JOIN beacon.notifications n ON n.id = d.notification_id
        WHERE n.tenant_id = :tenant_id
          AND n.recipient = :subject_email
        ORDER BY d.created_at DESC
        LIMIT 200
        """,
    ),
    (
        "suppression_entries",
        """
        SELECT id, identifier_type, identifier_value, reason, created_at
        FROM suppression.entries
        WHERE CAST(organization_id AS TEXT) = :tenant_id
          AND identifier_value = :subject_email
        ORDER BY created_at DESC
        LIMIT 200
        """,
    ),
)


class MessagingTenantDataDeleter(SubjectDataDeleter):
    supported_ops = frozenset({"delete", "anonymization"})

    async def delete(self, ctx: DSARDeleterContext) -> DSARDeleteOutcome:
        sm = _session_ctx()
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


# Hard-delete: the subject's suppression entries (opt-out preferences keyed on
# the PII identifier itself). These carry no independent legal-retention basis
# once the subject is erased.
_SOFT_DELETE_SQL: tuple[tuple[str, str], ...] = (
    (
        "suppression_entries",
        """
        DELETE FROM suppression.entries
        WHERE CAST(organization_id AS TEXT) = :tenant_id
          AND identifier_value = :subject_email
        RETURNING id
        """,
    ),
)


# Retain-under-legal-basis + redact: notification + delivery rows must be kept
# for audit/billing/anti-fraud (LGPD Art. 16) but the recipient PII is
# overwritten. No ``pii_redacted`` flag exists on these tables, so idempotency
# comes from the ``NOT LIKE 'redacted-%'`` guard. The redaction key uses the
# row id so it stays unique + reversible-proof.
_RETAINED_SQL: tuple[tuple[str, str], ...] = (
    (
        "notifications",
        """
        UPDATE beacon.notifications
        SET recipient = concat('redacted-', id, '@deleted.invalid'),
            payload = '{}'
        WHERE tenant_id = :tenant_id
          AND recipient = :subject_email
          AND recipient NOT LIKE 'redacted-%'
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

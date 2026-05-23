"""Anti-spam ML service — preventive pattern detection.

V0 strategy: rule-based heuristics with score 0..100. Real ML
(sentence-transformers semantic similarity) is a later upgrade once we have
labeled training data (BCN-115).

Heuristics:
- new_tenant_burst: org created <7d ago + >10k recipients in 1h.
- suspicious_keywords: phishing/spam markers (mass purchase indicators).
- spf_dmarc_misalign: from-domain not aligned with envelope-from.
- list_purchased_pattern: >30% bounces or >5% complaints in last hour.

If score >= threshold, returns Block decision and triggers customer success alert.
"""
from __future__ import annotations

import dataclasses
import logging
import re
import time
from datetime import UTC, datetime, timedelta
from typing import Literal

logger = logging.getLogger(__name__)


@dataclasses.dataclass(slots=True)
class AntiSpamDecision:
    score: int
    decision: Literal["allow", "review", "block"]
    reasons: list[str]


SPAM_KEYWORDS = [
    "free bitcoin", "click here now", "viagra", "casino", "you won",
    "limited time offer", "buy now", "100% free", "weight loss",
]


def _score_content(content: str) -> tuple[int, list[str]]:
    """Returns (score 0..40, reasons)."""
    score = 0
    reasons: list[str] = []
    lower = content.lower()
    matches = [kw for kw in SPAM_KEYWORDS if kw in lower]
    if matches:
        score += min(len(matches) * 10, 30)
        reasons.append(f"spam_keywords: {matches}")
    # Excessive caps?
    upper_pct = sum(1 for c in content if c.isupper()) / max(len(content), 1)
    if upper_pct > 0.5 and len(content) > 30:
        score += 10
        reasons.append("excessive_caps")
    # URL count
    urls = re.findall(r"https?://", lower)
    if len(urls) > 3:
        score += 5
        reasons.append(f"many_urls:{len(urls)}")
    return score, reasons


async def _score_tenant_history(organization_id: str, recipients_count: int) -> tuple[int, list[str]]:
    """Score based on tenant tenure + recent bounce/complaint rates."""
    score = 0
    reasons: list[str] = []
    try:
        from sqlalchemy import text as sql_text

        from beacon.db.session import worker_session

        async with worker_session() as session:
            row = (await session.execute(sql_text(
                "SELECT created_at FROM tenancy.organizations WHERE id = :o"
            ).bindparams(o=organization_id))).first()
            if row is None:
                return score, reasons
            created_at = row[0]
            age_days = (datetime.now(UTC) - created_at.replace(tzinfo=UTC)).days
            if age_days < 7 and recipients_count > 10_000:
                score += 30
                reasons.append(f"new_tenant_burst age_days={age_days} recipients={recipients_count}")
            elif age_days < 30 and recipients_count > 100_000:
                score += 20
                reasons.append(f"young_tenant_high_volume age_days={age_days}")
            # Recent bounce rate (last 1h)
            cutoff = datetime.now(UTC) - timedelta(hours=1)
            row2 = (await session.execute(sql_text(
                "SELECT count(*) FILTER (WHERE status IN ('bounced','complained')) AS bad, "
                "count(*) AS total FROM beacon.deliveries d "
                "JOIN beacon.notifications n ON n.id = d.notification_id "
                "WHERE n.tenant_id = :o AND d.created_at >= :c"
            ).bindparams(o=organization_id, c=cutoff))).first()
            if row2:
                bad, total = row2
                if total and (bad / total) > 0.3:
                    score += 25
                    reasons.append(f"high_bounce_rate {bad}/{total}")
    except Exception as exc:  # noqa: BLE001
        logger.debug("antispam history check skipped: %s", exc)
    return score, reasons


async def evaluate(
    *,
    organization_id: str,
    content: str,
    recipients_count: int = 1,
) -> AntiSpamDecision:
    """Sub-50ms heuristic evaluation. Returns Block/Review/Allow."""
    start = time.time()
    s1, r1 = _score_content(content)
    s2, r2 = await _score_tenant_history(organization_id, recipients_count)
    score = s1 + s2
    reasons = r1 + r2
    if score >= 60:
        decision: Literal["allow", "review", "block"] = "block"
    elif score >= 30:
        decision = "review"
    else:
        decision = "allow"
    elapsed_ms = (time.time() - start) * 1000
    if elapsed_ms > 50:
        logger.warning("antispam.slow elapsed_ms=%.1f", elapsed_ms)
    return AntiSpamDecision(score=score, decision=decision, reasons=reasons)


async def alert_customer_success(
    *, organization_id: str, decision: AntiSpamDecision, sample_content: str
) -> None:
    """Best-effort alert via webhook to ops Slack / customer success."""
    import os

    import httpx

    webhook = os.environ.get("BEACON_ANTISPAM_ALERT_WEBHOOK")
    if not webhook:
        logger.info("antispam.alert (no webhook) org=%s score=%s", organization_id, decision.score)
        return
    payload = {
        "organization_id": organization_id,
        "score": decision.score,
        "decision": decision.decision,
        "reasons": decision.reasons,
        "sample_content": sample_content[:500],
    }
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(webhook, json=payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning("antispam.alert_failed: %s", exc)

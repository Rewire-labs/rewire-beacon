"""Pricing pass-through service for SMS/WhatsApp pricing transparency.

Per BEACON.md §2.2.2: cost_zenvia ~R$ 0.07; BEACON charges R$ 0.07-0.12
(markup ~30%). Customer sees transparent breakdown.

Markup table is also exposed via `GET /v1/billing/pricing` (BCN-135).
"""
from __future__ import annotations

import dataclasses

# Markup percentages by tier and channel.
MARKUP_BPS = {  # basis points (1bp = 0.01%)
    ("sms", "hobby"): 5000,       # 50% markup
    ("sms", "starter"): 4000,     # 40%
    ("sms", "scale"): 3000,       # 30%
    ("sms", "enterprise"): 2500,  # 25%
    ("whatsapp", "hobby"): 5000,
    ("whatsapp", "starter"): 4000,
    ("whatsapp", "scale"): 3000,
    ("whatsapp", "enterprise"): 2500,
}


@dataclasses.dataclass(slots=True)
class PriceQuote:
    channel: str
    tier: str
    cost_brl_cents: int     # pass-through provider cost
    markup_bps: int
    customer_brl_cents: int


def quote(*, channel: str, tier: str, provider_cost_cents: int) -> PriceQuote:
    bps = MARKUP_BPS.get((channel, tier), 4000)
    markup_cents = int(provider_cost_cents * bps / 10000)
    return PriceQuote(
        channel=channel,
        tier=tier,
        cost_brl_cents=provider_cost_cents,
        markup_bps=bps,
        customer_brl_cents=provider_cost_cents + markup_cents,
    )

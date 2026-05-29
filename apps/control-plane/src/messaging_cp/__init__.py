"""messaging_cp — canonical namespace for rewire-messaging control-plane (V0).

Spec ADR 0108 C2 renames the legacy ``beacon.*`` package to ``messaging_cp.*``.
For V0 we keep both packages live: ``beacon.*`` remains the implementation
home (78% already shipped pre-consolidation), and ``messaging_cp.*`` exposes
the canonical surface required by the V0 dispatch prompt:

- adapters/{email,sms,push}/{postal,resend,zenvia,apns,fcm,router}.py
- queues/{sender_worker,retry_worker}.py
- api/v1/{emails,sms,push,webhooks,templates}.py

Each module is a thin wrapper that re-exports the existing implementation
under the canonical name. This lets us migrate import paths gradually
without recreating 78% of the code.
"""

from __future__ import annotations

__all__: list[str] = []
__version__ = "0.2.0"

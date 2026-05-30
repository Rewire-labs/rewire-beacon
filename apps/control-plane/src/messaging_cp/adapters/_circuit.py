"""Shared circuit-breaker for messaging_cp adapters.

RW-MESSAGING-23: extracted from the three duplicate _Circuit dataclasses
in email/router.py, sms/router.py, push/router.py to avoid drift.

States:
  - ``closed``   — normal operation.
  - ``open``     — skip this provider; re-probe after ``reset_after_seconds``.
  - ``half_open``— try one request; success → closed, failure → open again.
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(slots=True)
class ProviderCircuit:
    """Lightweight per-provider circuit breaker (in-process, no external state).

    Usage::

        cb = ProviderCircuit(failure_threshold=3, reset_after_seconds=30.0)
        if cb.is_open():
            raise ProviderCircuitOpen(...)
        try:
            result = await provider.send(...)
            cb.record_success()
        except ProviderError:
            cb.record_failure()
            raise
    """

    failure_threshold: int = 3
    reset_after_seconds: float = 30.0
    _failures: int = 0
    _opened_at: float = 0.0
    _state: str = "closed"

    def is_open(self) -> bool:
        """Return True if circuit is open (caller should skip this provider)."""
        if self._state != "open":
            return False
        if time.monotonic() - self._opened_at >= self.reset_after_seconds:
            self._state = "half_open"
            return False
        return True

    def record_success(self) -> None:
        """Reset failure counter and close the circuit."""
        self._failures = 0
        self._state = "closed"

    def record_failure(self) -> None:
        """Increment failure counter; open the circuit when threshold is hit."""
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._state = "open"
            self._opened_at = time.monotonic()

    @property
    def state(self) -> str:
        """Current state string: 'closed' | 'open' | 'half_open'."""
        return self._state


# Backward-compat alias used by router tests that imported _Circuit directly.
_Circuit = ProviderCircuit

__all__ = ["ProviderCircuit", "_Circuit"]

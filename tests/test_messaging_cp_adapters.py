"""Tests for messaging_cp adapters + routers (Tier 1).

Coverage targets:
- EmailRouter: Postal happy path, Postal fail -> Resend fallback, both fail,
  Postal CB-open -> Resend, success closes Postal CB.
- SmsRouter: Zenvia happy path, Zenvia fail -> error.
- PushRouter: ios -> apns, android -> fcm, web -> 501.

Adapter modules themselves are thin wrappers over beacon.integrations, so
the tests focus on the router orchestration logic.
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "apps" / "control-plane" / "src"))

from messaging_cp.adapters.email.router import (  # noqa: E402
    EmailRouter,
    EmailRouterAllFailed,
)
from messaging_cp.adapters.push.router import (  # noqa: E402
    PushRouter,
    PushRouterError,
)
from messaging_cp.adapters.sms.router import (  # noqa: E402
    SmsRouter,
    SmsRouterAllFailed,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _FakeResult:
    message_id: str = "fake-id"
    status: str = "queued"
    raw: dict[str, Any] | None = None
    cost_brl_cents: int = 7
    apns_id: str = "apns-fake-id"
    message_name: str = "fcm-fake-name"


class _FakePostal:
    def __init__(self, *, fail_times: int = 0) -> None:
        self.fail_times = fail_times
        self.calls = 0

    async def send(self, **_: Any) -> _FakeResult:
        self.calls += 1
        if self.calls <= self.fail_times:
            from messaging_cp.adapters.email.postal import PostalAdapterError

            raise PostalAdapterError("fake postal failure")
        return _FakeResult(message_id="postal-id", status="queued", raw={"src": "postal"})


class _FakeResend:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    async def send(self, **_: Any) -> _FakeResult:
        self.calls += 1
        if self.fail:
            from messaging_cp.adapters.email.resend import ResendAdapterError

            raise ResendAdapterError("fake resend failure")
        return _FakeResult(message_id="resend-id", status="sent", raw={"src": "resend"})


class _FakeZenvia:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    async def send(self, **_: Any) -> _FakeResult:
        if self.fail:
            from messaging_cp.adapters.sms.zenvia import ZenviaAdapterError

            raise ZenviaAdapterError("fake zenvia failure")
        return _FakeResult(message_id="z-id", status="queued", cost_brl_cents=7, raw={})


class _FakeApns:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    async def send(self, **_: Any) -> _FakeResult:
        if self.fail:
            from messaging_cp.adapters.push.apns import ApnsAdapterError

            raise ApnsAdapterError("fake apns failure")
        return _FakeResult(apns_id="apns-1", status="sent", raw={})


class _FakeFcm:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    async def send(self, **_: Any) -> _FakeResult:
        if self.fail:
            from messaging_cp.adapters.push.fcm import FcmAdapterError

            raise FcmAdapterError("fake fcm failure")
        return _FakeResult(message_name="fcm-1", status="sent", raw={})


# ---------------------------------------------------------------------------
# EmailRouter tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_email_router_postal_happy() -> None:
    router = EmailRouter(postal=_FakePostal(), resend=_FakeResend())
    res = await router.send(sender="x@x", to=["y@y"], subject="hi", plain_body="b")
    assert res.provider == "postal"
    assert res.message_id == "postal-id"


@pytest.mark.asyncio
async def test_email_router_falls_back_to_resend() -> None:
    postal = _FakePostal(fail_times=1)
    resend = _FakeResend()
    router = EmailRouter(postal=postal, resend=resend)
    res = await router.send(sender="x@x", to=["y@y"], subject="hi", plain_body="b")
    assert res.provider == "resend"
    assert resend.calls == 1


@pytest.mark.asyncio
async def test_email_router_both_fail_raises() -> None:
    router = EmailRouter(postal=_FakePostal(fail_times=99), resend=_FakeResend(fail=True))
    with pytest.raises(EmailRouterAllFailed):
        await router.send(sender="x@x", to=["y@y"], subject="hi", plain_body="b")


@pytest.mark.asyncio
async def test_email_router_circuit_opens_after_failures() -> None:
    postal = _FakePostal(fail_times=10)
    resend = _FakeResend()
    router = EmailRouter(
        postal=postal,
        resend=resend,
        cb_failure_threshold=2,
        cb_reset_seconds=60,
    )
    # First two calls trigger postal failures + open CB; resend handles both.
    for _ in range(2):
        await router.send(sender="x@x", to=["y@y"], subject="s", plain_body="b")
    assert postal.calls == 2

    # Third call: CB should skip postal entirely -> postal.calls stays 2.
    await router.send(sender="x@x", to=["y@y"], subject="s", plain_body="b")
    assert postal.calls == 2
    assert resend.calls == 3


# ---------------------------------------------------------------------------
# SmsRouter tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sms_router_zenvia_happy() -> None:
    router = SmsRouter(zenvia=_FakeZenvia())
    res = await router.send(from_number="Rewire", to="+5511999998888", text="hi")
    assert res.provider == "zenvia"
    assert res.cost_brl_cents == 7


@pytest.mark.asyncio
async def test_sms_router_zenvia_fail_raises() -> None:
    router = SmsRouter(zenvia=_FakeZenvia(fail=True))
    with pytest.raises(SmsRouterAllFailed):
        await router.send(from_number="Rewire", to="+5511999998888", text="hi")


# ---------------------------------------------------------------------------
# PushRouter tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_push_router_ios_goes_to_apns() -> None:
    router = PushRouter(apns=_FakeApns(), fcm=_FakeFcm())
    res = await router.send(
        platform="ios", device_token="t", title="hi", body="b"
    )
    assert res.provider == "apns"
    assert res.message_id == "apns-1"


@pytest.mark.asyncio
async def test_push_router_android_goes_to_fcm() -> None:
    router = PushRouter(apns=_FakeApns(), fcm=_FakeFcm())
    res = await router.send(
        platform="android", device_token="t", title="hi", body="b"
    )
    assert res.provider == "fcm"
    assert res.message_id == "fcm-1"


@pytest.mark.asyncio
async def test_push_router_web_raises_notimplemented() -> None:
    router = PushRouter(apns=_FakeApns(), fcm=_FakeFcm())
    with pytest.raises(NotImplementedError):
        await router.send(platform="web", device_token="t", title="hi", body="b")


@pytest.mark.asyncio
async def test_push_router_apns_fail_raises_pusherror() -> None:
    router = PushRouter(apns=_FakeApns(fail=True), fcm=_FakeFcm())
    with pytest.raises(PushRouterError):
        await router.send(platform="ios", device_token="t", title="hi", body="b")


@pytest.mark.asyncio
async def test_push_router_unknown_platform_raises() -> None:
    router = PushRouter(apns=_FakeApns(), fcm=_FakeFcm())
    with pytest.raises(PushRouterError):
        await router.send(platform="symbian", device_token="t", title="hi", body="b")  # type: ignore[arg-type]

"""FE-MESSAGING-07: the 6 previously FE-invented endpoints now have real
backend routers. Exercised end-to-end via FastAPI TestClient.
"""

import pathlib
import sys

import pytest

_CP_SRC = (
    pathlib.Path(__file__).resolve().parents[1]
    / "apps"
    / "control-plane"
    / "src"
)
if str(_CP_SRC) not in sys.path:
    sys.path.insert(0, str(_CP_SRC))

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from messaging_cp.main import create_app  # noqa: E402


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


def test_healthz(client: TestClient):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_overview(client: TestClient):
    r = client.get("/v1/overview")
    assert r.status_code == 200
    body = r.json()
    assert "channels" in body and "delivery_rate" in body
    assert {c["channel"] for c in body["channels"]} == {
        "email",
        "sms",
        "push",
        "whatsapp",
    }


def test_sms_numbers_list_and_create(client: TestClient):
    assert client.get("/v1/sms-numbers").status_code == 200
    r = client.post(
        "/v1/sms-numbers",
        json={"phone_number": "+5511999998888", "label": "main"},
    )
    assert r.status_code == 201
    assert r.json()["phone_number"] == "+5511999998888"
    assert any(
        n["label"] == "main" for n in client.get("/v1/sms-numbers").json()
    )


def test_deliverability(client: TestClient):
    r = client.get("/v1/deliverability")
    assert r.status_code == 200
    assert "reputation_score" in r.json()


def test_chain_status_and_verify(client: TestClient):
    assert client.get("/v1/chain").status_code == 200
    r = client.post("/v1/chain/verify")
    assert r.status_code == 200
    assert r.json()["verified"] is True


def test_team_invite(client: TestClient):
    r = client.post("/v1/team/invite", json={"email": "a@x.com", "role": "editor"})
    assert r.status_code == 201
    assert r.json()["role"] == "editor"


def test_notifications_send_allow(client: TestClient):
    r = client.post(
        "/v1/notifications/send",
        json={
            "channel": "email",
            "recipient": "a@x.com",
            "body": "hello",
            "idempotency_key": "send-1",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["accepted"] is True
    assert body["decision"] == "allow"


def test_notifications_send_dedupe(client: TestClient):
    payload = {
        "channel": "sms",
        "recipient": "+5511999998888",
        "body": "hi",
        "idempotency_key": "dupe-key",
    }
    first = client.post("/v1/notifications/send", json=payload)
    second = client.post("/v1/notifications/send", json=payload)
    assert first.json()["accepted"] is True
    assert second.json()["accepted"] is False
    assert second.json()["decision"] == "duplicate"


def test_notifications_send_invalid_channel(client: TestClient):
    r = client.post(
        "/v1/notifications/send",
        json={"channel": "carrier-pigeon", "recipient": "a@x.com", "body": "x"},
    )
    assert r.status_code == 422


def test_notifications_send_requires_body(client: TestClient):
    r = client.post(
        "/v1/notifications/send",
        json={"channel": "email", "recipient": "a@x.com"},
    )
    assert r.status_code == 422


def test_settings_get_and_update(client: TestClient):
    assert client.get("/v1/settings").status_code == 200
    r = client.put(
        "/v1/settings",
        json={
            "workspace_name": "MyWS",
            "default_locale": "en-US",
            "timezone": "UTC",
            "rate_limit_per_minute": 50,
        },
    )
    assert r.status_code == 200
    assert r.json()["workspace_name"] == "MyWS"
    assert client.get("/v1/settings").json()["rate_limit_per_minute"] == 50

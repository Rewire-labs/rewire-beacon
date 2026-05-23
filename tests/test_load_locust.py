"""Locust load test scenario — `locust -f tests/test_load_locust.py`.

Target: 1000 RPS sustained on /v1/messages/email (excludes Postal).
Provide a valid API token via env BEACON_LOAD_TOKEN to authenticate.
"""
from __future__ import annotations

import os
import uuid

try:
    from locust import HttpUser, between, task  # type: ignore
except ImportError:  # pragma: no cover
    HttpUser = object  # type: ignore
    between = lambda *a, **k: None  # noqa: E731

    def task(f):  # noqa: ANN001
        return f


TOKEN = os.environ.get("BEACON_LOAD_TOKEN", "bcn_live_placeholder")
ORG = os.environ.get("BEACON_LOAD_ORG", "00000000-0000-0000-0000-000000000000")
SENDER = os.environ.get("BEACON_LOAD_SENDER", "load@example.com")
RECIPIENT = os.environ.get("BEACON_LOAD_RECIPIENT", "to@example.com")


class BeaconUser(HttpUser):  # type: ignore[misc]
    wait_time = between(0.05, 0.2)

    def on_start(self) -> None:
        self.client.headers.update({
            "Authorization": f"Bearer {TOKEN}",
            "X-Organization-Id": ORG,
            "Content-Type": "application/json",
        })

    @task(10)
    def send_email(self) -> None:
        body = {
            "sender": SENDER,
            "to": [RECIPIENT],
            "subject": f"load-test-{uuid.uuid4().hex[:8]}",
            "html_body": "<p>hi</p>",
            "plain_body": "hi",
            "consent_basis": "consent",
        }
        self.client.post("/v1/messages/email", json=body, headers={"Idempotency-Key": str(uuid.uuid4())})

    @task(1)
    def list_suppression(self) -> None:
        self.client.get("/v1/suppression?limit=20")

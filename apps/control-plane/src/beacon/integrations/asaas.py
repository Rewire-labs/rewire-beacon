"""Asaas BR — payment gateway client (boleto + PIX + cards + recurring).

Canonical Rewire BR gateway (alternative to Stripe given BR-first focus).
"""
from __future__ import annotations

import dataclasses
import os
from datetime import date
from typing import Any

import httpx


@dataclasses.dataclass(slots=True)
class AsaasCharge:
    charge_id: str
    invoice_url: str
    bank_slip_url: str | None
    pix_qr_code: str | None
    status: str
    raw: dict[str, Any]


class AsaasError(RuntimeError):
    pass


class AsaasClient:
    def __init__(self, *, api_key: str | None = None, sandbox: bool = False, timeout: float = 10.0) -> None:
        self.api_key = api_key or os.environ.get("BEACON_ASAAS_API_KEY", "")
        self.base_url = "https://sandbox.asaas.com/api/v3" if sandbox else "https://www.asaas.com/api/v3"
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "access_token": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def create_charge(
        self,
        *,
        customer_id: str,
        billing_type: str,  # BOLETO|CREDIT_CARD|PIX|UNDEFINED
        value_brl: float,
        due_date: date,
        description: str,
        external_reference: str,
    ) -> AsaasCharge:
        payload = {
            "customer": customer_id,
            "billingType": billing_type,
            "value": value_brl,
            "dueDate": due_date.isoformat(),
            "description": description,
            "externalReference": external_reference,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self.base_url}/payments", json=payload, headers=self._headers())
        if resp.status_code >= 400:
            raise AsaasError(f"asaas charge failed [{resp.status_code}]: {resp.text}")
        d = resp.json()
        return AsaasCharge(
            charge_id=str(d.get("id", "")),
            invoice_url=d.get("invoiceUrl", ""),
            bank_slip_url=d.get("bankSlipUrl"),
            pix_qr_code=d.get("encodedImage"),
            status=d.get("status", "PENDING"),
            raw=d,
        )


__all__ = ["AsaasClient", "AsaasCharge", "AsaasError"]

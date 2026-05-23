"""NFe.io HTTP client — automated NF-e (Brazilian electronic invoice) issuance.

We use NFe.io as it's the canonical BR invoice provider Rewire uses; it
abstracts the SEFAZ municipal/state APIs.
"""
from __future__ import annotations

import dataclasses
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclasses.dataclass(slots=True)
class NfeIssueResult:
    nfe_id: str
    status: str
    raw: dict[str, Any]


class NfeError(RuntimeError):
    pass


class NfeIoClient:
    def __init__(self, *, api_key: str | None = None, company_id: str | None = None, timeout: float = 15.0) -> None:
        self.api_key = api_key or os.environ.get("BEACON_NFEIO_API_KEY", "")
        self.company_id = company_id or os.environ.get("BEACON_NFEIO_COMPANY_ID", "")
        self.base_url = "https://api.nfe.io"
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def issue_service_invoice(
        self,
        *,
        borrower_cnpj: str,
        services_amount_cents: int,
        description: str,
        external_id: str,
    ) -> NfeIssueResult:
        payload = {
            "borrower": {"federalTaxNumber": borrower_cnpj},
            "cityServiceCode": "0103",  # service - software/IT
            "description": description,
            "servicesAmount": services_amount_cents / 100,
            "externalId": external_id,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self.base_url}/v1/companies/{self.company_id}/serviceinvoices",
                json=payload,
                headers=self._headers(),
            )
        if resp.status_code >= 400:
            raise NfeError(f"nfe issue failed [{resp.status_code}]: {resp.text}")
        data = resp.json()
        return NfeIssueResult(nfe_id=str(data.get("id", "")), status=data.get("flowStatus", "Issued"), raw=data)


__all__ = ["NfeIoClient", "NfeError", "NfeIssueResult"]

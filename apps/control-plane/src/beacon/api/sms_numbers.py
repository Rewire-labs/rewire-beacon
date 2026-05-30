"""SMS sender-number management router (FE-MESSAGING-07)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/sms-numbers", tags=["sms-numbers"])


class SmsNumber(BaseModel):
    id: str
    phone_number: str = Field(..., description="E.164 format")
    label: str = ""
    provider: str = "zenvia"
    verified: bool = False


class SmsNumberCreate(BaseModel):
    phone_number: str
    label: str = ""
    provider: str = "zenvia"


# in-memory store; replaced by DB-backed repo in production wiring
_NUMBERS: dict[str, SmsNumber] = {}


@router.get("", response_model=list[SmsNumber])
def list_numbers() -> list[SmsNumber]:
    return list(_NUMBERS.values())


@router.post("", response_model=SmsNumber, status_code=201)
def create_number(payload: SmsNumberCreate) -> SmsNumber:
    new_id = f"num_{len(_NUMBERS) + 1}"
    number = SmsNumber(
        id=new_id,
        phone_number=payload.phone_number,
        label=payload.label,
        provider=payload.provider,
        verified=False,
    )
    _NUMBERS[new_id] = number
    return number

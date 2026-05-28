from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ClaimCreate(BaseModel):
    service_date: date
    billed_amount: Decimal
    payer_id: str | None = None  # if None, derived from patient.mco in service layer
    diagnosis_codes: list[str] = []
    procedure_codes: list[str] = []
    claim_data: dict | None = None  # additional raw claim fields


class ClaimRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    provider_id: uuid.UUID
    availity_claim_id: str | None
    status: str | None
    service_date: date | None
    billed_amount: Decimal | None
    paid_amount: Decimal | None
    payer_id: str | None
    submitted_at: datetime | None
    status_checked_at: datetime | None
    created_at: datetime
    updated_at: datetime

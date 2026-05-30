from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ClaimCreate(BaseModel):
    visit_type: str  # determines procedure_code, modifier, rate, and diag_codes automatically
    service_date: date
    location_type: str | None = None  # 'in_person' → POS 12, 'telehealth' → POS 02
    payer_id: str | None = None  # if None, derived from patient.mco in service layer
    # billed_amount, diagnosis_codes, procedure_codes derived from visit_type via billing_constants
    billed_amount: Decimal | None = None  # override; auto-calculated if not provided
    diagnosis_codes: list[str] = []      # override; auto-calculated if empty
    procedure_codes: list[str] = []      # override; auto-calculated if empty
    claim_data: dict | None = None       # additional raw claim fields


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

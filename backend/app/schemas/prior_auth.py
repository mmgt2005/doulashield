from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class PriorAuthCreate(BaseModel):
    service_type: str
    start_date: date
    end_date: date | None = None
    diagnosis_codes: list[str] = []
    procedure_codes: list[str] = []
    auth_data: dict | None = None  # additional raw auth fields


class PriorAuthRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    provider_id: uuid.UUID
    availity_auth_id: str | None
    status: str | None
    service_type: str | None
    start_date: date | None
    end_date: date | None
    submitted_at: datetime | None
    status_checked_at: datetime | None
    created_at: datetime
    updated_at: datetime

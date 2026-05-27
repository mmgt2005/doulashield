import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class PrenatalLogCreate(BaseModel):
    log_type: Literal["prenatal", "postnatal"]
    entry: str
    entry_date: date


class PrenatalLogRead(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    provider_id: uuid.UUID
    log_type: str
    entry: str
    entry_date: date
    created_at: datetime

    model_config = {"from_attributes": True}

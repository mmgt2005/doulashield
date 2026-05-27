import uuid
from datetime import date, datetime, time

from pydantic import BaseModel


class BirthLogCreate(BaseModel):
    birth_date: date
    birth_time: time | None = None
    birth_location: str | None = None
    notes: str | None = None


class BirthLogRead(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    provider_id: uuid.UUID
    birth_date: date
    birth_time: time | None
    birth_location: str | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

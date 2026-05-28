import uuid
from datetime import date, datetime

from pydantic import BaseModel


class SOAPNoteCreate(BaseModel):
    visit_date: date
    subjective: str | None = None
    objective: str | None = None
    assessment: str | None = None
    plan: str | None = None
    source_image_path: str | None = None


class SOAPNoteUpdate(BaseModel):
    visit_date: date | None = None
    subjective: str | None = None
    objective: str | None = None
    assessment: str | None = None
    plan: str | None = None


class SOAPNoteRead(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    provider_id: uuid.UUID
    visit_date: date
    subjective: str | None
    objective: str | None
    assessment: str | None
    plan: str | None
    source_image_path: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

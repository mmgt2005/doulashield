from __future__ import annotations

import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict


class VisitCreate(BaseModel):
    visit_date: date | None = None
    subjective: str | None = None
    objective: str | None = None
    assessment: str | None = None
    plan: str | None = None
    entry: str | None = None
    birth_time: time | None = None
    birth_location: str | None = None
    birth_notes: str | None = None
    source_image_path: str | None = None


class VisitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    provider_id: uuid.UUID
    visit_type: str
    visit_date: date | None
    subjective: str | None
    objective: str | None
    assessment: str | None
    plan: str | None
    entry: str | None
    birth_time: time | None
    birth_location: str | None
    birth_notes: str | None
    source_image_path: str | None
    created_at: datetime
    updated_at: datetime

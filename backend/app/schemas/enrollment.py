import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

PathwayLiteral = Literal["education_training", "experienced"]
TaskStatusLiteral = Literal["not_started", "in_progress", "complete"]
ServiceStatusLiteral = Literal["in_progress", "submitted", "complete", "cancelled"]


class EnrollmentServiceCreate(BaseModel):
    provider_id: uuid.UUID
    pcb_pathway: PathwayLiteral
    intake_data: dict[str, Any] | None = None


class EnrollmentServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider_id: uuid.UUID
    created_by: uuid.UUID | None
    pcb_pathway: str | None
    status: str
    intake_data: dict[str, Any] | None
    pcb_cert_date: date | None
    created_at: datetime
    updated_at: datetime


class EnrollmentTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    service_id: uuid.UUID
    task_key: str
    required_pathway: str
    label: str
    description: str | None
    status: str
    task_data: dict[str, Any] | None
    notes: str | None
    sort_order: int
    completed_at: datetime | None
    created_at: datetime


class EnrollmentTaskUpdate(BaseModel):
    status: TaskStatusLiteral | None = None
    notes: str | None = None
    task_data: dict[str, Any] | None = None


class EnrollmentDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    service_id: uuid.UUID
    task_id: uuid.UUID | None
    uploaded_by: uuid.UUID | None
    file_name: str
    document_type: str | None
    created_at: datetime


class EnrollmentServiceDetail(BaseModel):
    service: EnrollmentServiceRead
    tasks: list[EnrollmentTaskRead]
    documents: list[EnrollmentDocumentRead]
    provider_email: str | None = None
    provider_name: str | None = None


class CompletePcbRequest(BaseModel):
    cert_date: date

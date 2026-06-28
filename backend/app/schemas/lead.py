import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr

SourceLiteral = Literal["webinar", "quiz", "manual", "contact_form"]
StatusLiteral = Literal["new", "contacted", "qualified", "demo_scheduled", "converted", "not_interested"]
ProviderTypeLiteral = Literal["independent", "agency", "unknown"]


class WebinarLeadCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None = None
    webinar_topic: str | None = None
    organization_name: str | None = None


class QuizLeadCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None = None
    provider_type: ProviderTypeLiteral = "unknown"
    answers: dict[str, Any] | None = None
    organization_name: str | None = None


class ContactLeadCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None = None
    organization_name: str | None = None
    provider_type: ProviderTypeLiteral = "unknown"
    message: str | None = None


class LeadCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None = None
    organization_name: str | None = None
    provider_type: ProviderTypeLiteral = "unknown"
    source: SourceLiteral = "manual"
    notes: str | None = None
    lead_data: dict[str, Any] | None = None


class LeadUpdate(BaseModel):
    status: StatusLiteral | None = None
    notes: str | None = None
    follow_up_at: datetime | None = None
    assigned_to: uuid.UUID | None = None
    provider_type: ProviderTypeLiteral | None = None
    organization_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None


class LeadRead(BaseModel):
    id: uuid.UUID
    source: str
    status: str
    first_name: str
    last_name: str
    email: str
    phone: str | None
    organization_name: str | None
    provider_type: str
    lead_data: dict[str, Any] | None
    notes: str | None
    follow_up_at: datetime | None
    assigned_to: uuid.UUID | None
    converted_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}

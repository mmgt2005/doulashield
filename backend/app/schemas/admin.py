import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    role: Literal["provider", "admin"] = "provider"


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: Literal["provider", "admin"] | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    full_name: str | None
    mfa_enabled: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ProviderSettingsUpdate(BaseModel):
    npi: str | None = None
    availity_client_id: str | None = None
    availity_client_secret: str | None = None
    telehealth_link: str | None = None


class ProviderSettingsRead(BaseModel):
    npi: str | None
    availity_connected: bool
    telehealth_link: str | None


class AuditLogRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    resource_type: str | None
    resource_id: uuid.UUID | None
    ip_address: str | None
    user_agent: str | None
    extra_context: dict | None
    timestamp: datetime

    model_config = {"from_attributes": True}

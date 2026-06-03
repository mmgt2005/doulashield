import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr


class McoContract(BaseModel):
    mco: str
    contract_date: date | None = None


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
    contact_email: str | None = None
    zipzign_api_key: str | None = None  # plain text on write; encrypted on save; never returned
    zone: str | None = None       # e.g. 'SE' | 'SW' | 'LC' | 'NE' | 'NW'
    counties: list[str] | None = None  # county names within the selected zone
    provider_address: str | None = None
    provider_phone: str | None = None
    provider_ssn: str | None = None          # plain text on write; encrypted on save; never returned
    provider_signature_path: str | None = None
    billing_provider_name: str | None = None  # exact name as registered in PROMISe (used in CMS 1500 Box 33)
    mco_contracts: list[McoContract] | None = None
    caqh_last_attested_on: date | None = None
    promise_last_enrolled_on: date | None = None


class ProviderSettingsRead(BaseModel):
    npi: str | None
    availity_connected: bool
    telehealth_link: str | None
    contact_email: str | None
    zipzign_connected: bool
    zone: str | None
    counties: list[str] | None
    provider_address: str | None
    provider_phone: str | None
    provider_ssn_connected: bool
    provider_signature_path: str | None
    billing_provider_name: str | None
    mco_contracts: list[McoContract] | None
    caqh_last_attested_on: date | None
    caqh_days_remaining: int | None  # None = no date set; negative = overdue
    promise_last_enrolled_on: date | None
    promise_days_remaining: int | None  # None = no date set; negative = overdue


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

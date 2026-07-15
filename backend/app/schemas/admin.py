import uuid
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr

RoleLiteral = Literal["provider", "admin", "billing_admin"]


class McoContract(BaseModel):
    mco: str
    contract_date: date | None = None


class BillingProviderCreate(BaseModel):
    name: str
    group_npi: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None
    phone: str | None = None


class BillingProviderUpdate(BillingProviderCreate):
    name: str | None = None
    availity_client_id: str | None = None    # plain text on write; encrypted on save
    availity_client_secret: str | None = None  # plain text on write; never returned
    availity_npi: str | None = None


class BillingProviderRead(BillingProviderCreate):
    id: uuid.UUID
    stripe_subscription_id: str | None = None
    subscription_status: str | None = None
    created_at: datetime
    provider_count: int = 0
    availity_connected: bool = False
    availity_npi: str | None = None
    enrollment_tier_enabled: bool = False

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    role: RoleLiteral = "provider"
    managed_billing_provider_id: uuid.UUID | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: RoleLiteral | None = None
    is_active: bool | None = None
    is_demo: bool | None = None
    is_executive: bool | None = None
    billing_provider_id: uuid.UUID | None = None
    managed_billing_provider_id: uuid.UUID | None = None


class UserRead(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    full_name: str | None
    mfa_enabled: bool
    is_active: bool
    is_demo: bool = False
    is_executive: bool = False
    created_at: datetime
    last_sign_in_at: datetime | None = None
    welcome_email_sent_at: datetime | None = None
    tos_accepted_at: datetime | None = None
    billing_provider_id: uuid.UUID | None = None
    managed_billing_provider_id: uuid.UUID | None = None

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
    billing_provider_id: uuid.UUID | None = None  # link to shared billing entity
    mco_contracts: list[McoContract] | None = None
    caqh_last_attested_on: date | None = None
    promise_last_enrolled_on: date | None = None
    pcb_last_certified_on: date | None = None
    liability_insurance_expires_on: date | None = None


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
    billing_provider_id: uuid.UUID | None
    billing_provider: BillingProviderRead | None  # populated from JOIN when linked
    mco_contracts: list[McoContract] | None
    caqh_last_attested_on: date | None
    caqh_days_remaining: int | None  # None = no date set; negative = overdue
    promise_last_enrolled_on: date | None
    promise_days_remaining: int | None  # None = no date set; negative = overdue
    pcb_last_certified_on: date | None
    pcb_days_remaining: int | None  # None = no date set; negative = overdue
    liability_insurance_expires_on: date | None
    liability_days_remaining: int | None  # None = no date set; negative = overdue


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

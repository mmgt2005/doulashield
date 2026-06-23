import uuid
from datetime import date, datetime

from pydantic import BaseModel


class PatientCreate(BaseModel):
    name: str
    medicaid_id: str
    gender: str = "F"
    email: str | None = None
    mco: str | None = None
    date_of_birth: date | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    medicaid_card_image_path: str | None = None
    policy_group: str | None = None
    referring_provider_npi: str | None = None
    referring_provider_name: str | None = None
    has_other_insurance: bool = False
    ma589_signed_date: date | None = None


class PatientUpdate(BaseModel):
    name: str | None = None
    gender: str | None = None
    email: str | None = None
    mco: str | None = None
    date_of_birth: date | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    medicaid_card_image_path: str | None = None
    policy_group: str | None = None
    referring_provider_npi: str | None = None
    referring_provider_name: str | None = None
    has_other_insurance: bool | None = None
    ma589_signed_date: date | None = None
    # medicaid_id updates go through a separate admin-only flow


class PatientRead(BaseModel):
    id: uuid.UUID
    provider_id: uuid.UUID
    name: str           # Decrypted by service before returning
    gender: str
    email: str | None
    mco: str | None
    date_of_birth: date | None
    address: str | None
    latitude: float | None
    longitude: float | None
    medicaid_card_image_path: str | None
    policy_group: str | None
    referring_provider_npi: str | None
    referring_provider_name: str | None
    has_other_insurance: bool
    ma589_signed_date: date | None
    eligibility_status: str | None
    eligibility_checked_at: datetime | None
    is_active: bool
    is_demo: bool = False
    created_at: datetime
    updated_at: datetime
    # medicaid_id deliberately excluded — use GET /patients/{id}/medicaid-id

    model_config = {"from_attributes": True}


class PatientReadWithMedicaidId(PatientRead):
    medicaid_id: str    # Only returned from the privileged, separately audited endpoint


class PatientSearch(BaseModel):
    query: str          # POST body to avoid PHI in query string

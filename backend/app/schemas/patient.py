import uuid
from datetime import datetime

from pydantic import BaseModel


class PatientCreate(BaseModel):
    name: str
    medicaid_id: str
    mco: str | None = None


class PatientUpdate(BaseModel):
    name: str | None = None
    mco: str | None = None
    # medicaid_id updates go through a separate admin-only flow


class PatientRead(BaseModel):
    id: uuid.UUID
    provider_id: uuid.UUID
    name: str           # Decrypted by service before returning
    mco: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # medicaid_id deliberately excluded — use GET /patients/{id}/medicaid-id

    model_config = {"from_attributes": True}


class PatientReadWithMedicaidId(PatientRead):
    medicaid_id: str    # Only returned from the privileged, separately audited endpoint


class PatientSearch(BaseModel):
    query: str          # POST body to avoid PHI in query string

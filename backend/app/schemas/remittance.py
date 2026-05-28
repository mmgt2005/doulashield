from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class RemittanceFetchRequest(BaseModel):
    start_date: date
    end_date: date
    payer_id: str | None = None


class RemittanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider_id: uuid.UUID
    availity_remit_id: str | None
    check_number: str | None
    payer_id: str | None
    payment_date: date | None
    total_payment: Decimal | None
    fetched_at: datetime

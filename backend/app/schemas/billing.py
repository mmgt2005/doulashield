from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class BillingStatusRead(BaseModel):
    stripe_customer_id: str | None
    escrow_agreed_at: datetime | None
    escrow_agreement_version: str | None
    deposit_paid: bool
    deposit_paid_at: datetime | None
    escrow_balance_remaining: float
    subscription_status: str | None

    model_config = {"from_attributes": True}


class SignEscrowRequest(BaseModel):
    agreed: bool


class StartSubscriptionRequest(BaseModel):
    provider_user_id: uuid.UUID


class GenerateDepositLinkRequest(BaseModel):
    provider_user_id: uuid.UUID


class LinkStripeCustomerRequest(BaseModel):
    provider_user_id: uuid.UUID
    stripe_customer_id: str


class CreateAndInviteRequest(BaseModel):
    email: EmailStr
    full_name: str | None = None


class UserWithBillingRead(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    full_name: str | None
    is_active: bool
    stripe_customer_id: str | None
    escrow_agreed_at: datetime | None
    deposit_paid: bool
    deposit_paid_at: datetime | None
    escrow_balance_remaining: float
    subscription_status: str | None

    model_config = {"from_attributes": True}

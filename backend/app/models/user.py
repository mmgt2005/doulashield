import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)  # 'provider' | 'admin'
    full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    totp_secret: Mapped[str | None] = mapped_column(String, nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    npi: Mapped[str | None] = mapped_column(String(10), nullable=True)
    availity_client_id_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    availity_client_secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    uhc_client_id_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    uhc_client_secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    telehealth_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    zipzign_api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    zone: Mapped[str | None] = mapped_column(String(4), nullable=True)
    counties: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array e.g. '["Bucks","Chester"]'

    # Billing
    stripe_customer_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    escrow_agreed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    escrow_agreement_version: Mapped[str | None] = mapped_column(String(16), nullable=True)
    deposit_paid: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    deposit_paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    escrow_balance_remaining: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default="400.00", nullable=False)
    stripe_subscription_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    subscription_status: Mapped[str | None] = mapped_column(String(32), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    patients: Mapped[list["Patient"]] = relationship(back_populates="provider")  # type: ignore[name-defined]

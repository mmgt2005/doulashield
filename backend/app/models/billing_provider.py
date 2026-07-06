import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class BillingProvider(Base):
    __tablename__ = "billing_providers"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    group_npi: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str | None] = mapped_column(Text, nullable=True)
    zip: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    subscription_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False, default=False)
    enrollment_tier_enabled: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False, default=False)
    enrollment_tier_stripe_item_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    availity_client_id_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    availity_client_secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    availity_npi: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    providers: Mapped[list["User"]] = relationship(  # type: ignore[name-defined]
        "User",
        foreign_keys="User.billing_provider_id",
        back_populates="billing_provider",
    )
    billing_admins: Mapped[list["User"]] = relationship(  # type: ignore[name-defined]
        "User",
        foreign_keys="User.managed_billing_provider_id",
        back_populates="managed_billing_provider",
    )

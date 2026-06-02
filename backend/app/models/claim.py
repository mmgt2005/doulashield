import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Claim(Base):
    __tablename__ = "claims"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.patients.id"), nullable=False)
    provider_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.users.id"), nullable=False)
    availity_claim_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    visit_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_manual: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    service_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    billed_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    paid_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    payer_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    claim_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    raw_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    patient: Mapped["Patient"] = relationship()  # type: ignore[name-defined]
    provider: Mapped["User"] = relationship()  # type: ignore[name-defined]

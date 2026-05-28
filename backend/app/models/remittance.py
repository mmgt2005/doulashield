import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Remittance(Base):
    __tablename__ = "remittances"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.users.id"), nullable=False)
    availity_remit_id: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
    check_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    payer_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_payment: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    raw_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    provider: Mapped["User"] = relationship()  # type: ignore[name-defined]

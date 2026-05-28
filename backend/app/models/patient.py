import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("public.users.id"), nullable=False
    )
    # Fernet ciphertext — decrypted in service layer, never logged
    name_encrypted: Mapped[str] = mapped_column(String, nullable=False)
    medicaid_id_encrypted: Mapped[str] = mapped_column(String, nullable=False)
    mco: Mapped[str | None] = mapped_column(String, nullable=True)
    medicaid_card_image_path: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    provider: Mapped["User"] = relationship(back_populates="patients")  # type: ignore[name-defined]
    soap_notes: Mapped[list["SOAPNote"]] = relationship(back_populates="patient", cascade="all, delete-orphan")  # type: ignore[name-defined]
    prenatal_postnatal_logs: Mapped[list["PrenatalPostnatalLog"]] = relationship(back_populates="patient", cascade="all, delete-orphan")  # type: ignore[name-defined]
    birth_logs: Mapped[list["BirthLog"]] = relationship(back_populates="patient", cascade="all, delete-orphan")  # type: ignore[name-defined]

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, time

from sqlalchemy import CheckConstraint, Date, DateTime, Double, ForeignKey, String, Text, Time, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class VisitType(str, enum.Enum):
    prenatal_1 = "prenatal_1"
    prenatal_2 = "prenatal_2"
    prenatal_3 = "prenatal_3"
    prenatal_4 = "prenatal_4"
    prenatal_5 = "prenatal_5"
    prenatal_6 = "prenatal_6"
    labor = "labor"
    postnatal_1 = "postnatal_1"
    postnatal_2 = "postnatal_2"
    postnatal_3 = "postnatal_3"
    postnatal_4 = "postnatal_4"
    postnatal_5 = "postnatal_5"
    postnatal_6 = "postnatal_6"


class Visit(Base):
    __tablename__ = "visits"
    __table_args__ = (
        UniqueConstraint("patient_id", "visit_type", name="visits_patient_visit_type_unique"),
        CheckConstraint(
            "visit_type IN ("
            "'prenatal_1','prenatal_2','prenatal_3','prenatal_4','prenatal_5','prenatal_6',"
            "'labor',"
            "'postnatal_1','postnatal_2','postnatal_3','postnatal_4','postnatal_5','postnatal_6'"
            ")",
            name="visits_visit_type_check",
        ),
        {"schema": "public"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("public.patients.id"), nullable=False
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("public.users.id"), nullable=False
    )
    visit_type: Mapped[str] = mapped_column(Text, nullable=False)
    visit_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    subjective: Mapped[str | None] = mapped_column(Text, nullable=True)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    entry: Mapped[str | None] = mapped_column(Text, nullable=True)
    birth_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    birth_location: Mapped[str | None] = mapped_column(Text, nullable=True)
    birth_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_image_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    visit_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    visit_ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_latitude: Mapped[float | None] = mapped_column(Double, nullable=True)
    provider_longitude: Mapped[float | None] = mapped_column(Double, nullable=True)
    location_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    alternate_location: Mapped[str | None] = mapped_column(Text, nullable=True)
    ma91_signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ma91_signature_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    ma91_signed_by_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    ma91_zipzign_request_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    ma91_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    prior_auth_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    patient: Mapped["Patient"] = relationship(back_populates="visits")  # type: ignore[name-defined]

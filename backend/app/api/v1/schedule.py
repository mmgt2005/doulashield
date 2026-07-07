from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, cast, Date, or_
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_field
from app.dependencies import get_current_user, get_db
from app.models.patient import Patient
from app.models.visit import Visit

router = APIRouter(tags=["schedule"])

VISIT_LABELS: dict[str, str] = {
    "prenatal_1": "Prenatal 1",
    "prenatal_2": "Prenatal 2",
    "prenatal_3": "Prenatal 3",
    "prenatal_4": "Prenatal 4",
    "prenatal_5": "Prenatal 5",
    "prenatal_6": "Prenatal 6",
    "labor": "Labor",
    "postnatal_1": "Postnatal 1",
    "postnatal_2": "Postnatal 2",
    "postnatal_3": "Postnatal 3",
    "postnatal_4": "Postnatal 4",
    "postnatal_5": "Postnatal 5",
    "postnatal_6": "Postnatal 6",
    "crisis_loss_1": "Crisis/Loss Visit 1",
    "crisis_loss_2": "Crisis/Loss Visit 2",
}


class ScheduleEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    patient_id: uuid.UUID
    patient_name: str
    visit_type: str
    visit_label: str
    scheduled_at: datetime | None
    visit_date: date | None
    visit_started_at: datetime | None
    visit_ended_at: datetime | None
    status: str


def _today() -> date:
    return date.today()


def _today_plus_6() -> date:
    return date.today() + timedelta(days=6)


@router.get("/schedule", response_model=list[ScheduleEntry])
async def get_schedule(
    current_user: Annotated[object, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    date_from: date = Query(default_factory=_today),
    date_to: date = Query(default_factory=_today_plus_6),
) -> list[ScheduleEntry]:
    result = await db.execute(
        select(Visit, Patient.name_encrypted)
        .join(Patient, Patient.id == Visit.patient_id)
        .where(
            Visit.provider_id == current_user.id,
            Patient.is_active.is_(True),
            or_(
                and_(
                    Visit.scheduled_at.isnot(None),
                    cast(Visit.scheduled_at, Date).between(date_from, date_to),
                ),
                and_(
                    Visit.visit_date.isnot(None),
                    Visit.visit_date.between(date_from, date_to),
                ),
                and_(
                    Visit.visit_started_at.isnot(None),
                    cast(Visit.visit_started_at, Date).between(date_from, date_to),
                ),
            ),
        )
        .order_by(
            Visit.scheduled_at.asc().nullslast(),
            Visit.visit_date.asc().nullslast(),
            Visit.visit_started_at.asc().nullslast(),
        )
    )

    entries: list[ScheduleEntry] = []
    for visit, name_enc in result.all():
        if visit.visit_ended_at:
            status = "complete"
        elif visit.visit_started_at:
            status = "in_progress"
        elif visit.scheduled_at:
            status = "scheduled"
        else:
            status = "unscheduled"

        try:
            patient_name = decrypt_field(name_enc)
        except Exception:
            patient_name = "Unknown"

        entries.append(
            ScheduleEntry(
                patient_id=visit.patient_id,
                patient_name=patient_name,
                visit_type=visit.visit_type,
                visit_label=VISIT_LABELS.get(visit.visit_type, visit.visit_type),
                scheduled_at=visit.scheduled_at,
                visit_date=visit.visit_date,
                visit_started_at=visit.visit_started_at,
                visit_ended_at=visit.visit_ended_at,
                status=status,
            )
        )

    return entries

from __future__ import annotations

import uuid

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import AuditLogger
from app.models.visit import Visit, VisitType
from app.schemas.visit import VisitCreate, VisitRead


class VisitService:
    def __init__(self, db: AsyncSession, audit: AuditLogger) -> None:
        self._db = db
        self._audit = audit

    async def list_for_patient(self, patient_id: uuid.UUID) -> list[VisitRead]:
        result = await self._db.execute(
            select(Visit).where(Visit.patient_id == patient_id)
        )
        return [VisitRead.model_validate(v) for v in result.scalars().all()]

    async def get_by_type(
        self, patient_id: uuid.UUID, visit_type: VisitType
    ) -> VisitRead | None:
        result = await self._db.execute(
            select(Visit).where(
                Visit.patient_id == patient_id,
                Visit.visit_type == visit_type.value,
            )
        )
        visit = result.scalar_one_or_none()
        return VisitRead.model_validate(visit) if visit else None

    async def upsert(
        self,
        patient_id: uuid.UUID,
        provider_id: uuid.UUID,
        visit_type: VisitType,
        data: VisitCreate,
        ip: str,
        user_agent: str,
    ) -> VisitRead:
        values = {
            "patient_id": patient_id,
            "provider_id": provider_id,
            "visit_type": visit_type.value,
            **data.model_dump(exclude_unset=True),
        }
        update_set = {
            **data.model_dump(exclude_unset=True),
            "updated_at": func.now(),
        }

        stmt = (
            pg_insert(Visit)
            .values(**values)
            .on_conflict_do_update(
                constraint="visits_patient_visit_type_unique",
                set_=update_set,
            )
            .returning(Visit)
        )
        result = await self._db.execute(stmt)
        visit = result.scalar_one()
        await self._db.commit()
        await self._db.refresh(visit)

        await self._audit.log(
            action="UPSERT_VISIT",
            resource_type="visit",
            resource_id=visit.id,
            ip_address=ip,
            user_agent=user_agent,
            user_id=provider_id,
            extra_context={"visit_type": visit_type.value},
        )
        return VisitRead.model_validate(visit)

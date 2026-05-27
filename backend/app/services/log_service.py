from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import AuditLogger
from app.models.birth_log import BirthLog
from app.models.prenatal_postnatal_log import PrenatalPostnatalLog
from app.schemas.birth_log import BirthLogCreate, BirthLogRead
from app.schemas.prenatal_log import PrenatalLogCreate, PrenatalLogRead


class LogService:
    def __init__(self, db: AsyncSession, audit: AuditLogger) -> None:
        self._db = db
        self._audit = audit

    # ── Prenatal / Postnatal ──────────────────────────────────────────────────

    async def create_prenatal_log(
        self,
        patient_id: uuid.UUID,
        provider_id: uuid.UUID,
        data: PrenatalLogCreate,
        ip: str,
        user_agent: str,
    ) -> PrenatalLogRead:
        log = PrenatalPostnatalLog(
            patient_id=patient_id, provider_id=provider_id, **data.model_dump()
        )
        self._db.add(log)
        await self._db.commit()
        await self._db.refresh(log)

        await self._audit.log(
            action="CREATE",
            resource_type="prenatal_log",
            resource_id=log.id,
            ip_address=ip,
            user_agent=user_agent,
            user_id=provider_id,
        )
        return PrenatalLogRead.model_validate(log)

    async def list_prenatal_logs(self, patient_id: uuid.UUID) -> list[PrenatalLogRead]:
        result = await self._db.execute(
            select(PrenatalPostnatalLog).where(PrenatalPostnatalLog.patient_id == patient_id)
        )
        return [PrenatalLogRead.model_validate(r) for r in result.scalars().all()]

    # ── Birth Log ─────────────────────────────────────────────────────────────

    async def create_birth_log(
        self,
        patient_id: uuid.UUID,
        provider_id: uuid.UUID,
        data: BirthLogCreate,
        ip: str,
        user_agent: str,
    ) -> BirthLogRead:
        log = BirthLog(
            patient_id=patient_id, provider_id=provider_id, **data.model_dump()
        )
        self._db.add(log)
        await self._db.commit()
        await self._db.refresh(log)

        await self._audit.log(
            action="CREATE",
            resource_type="birth_log",
            resource_id=log.id,
            ip_address=ip,
            user_agent=user_agent,
            user_id=provider_id,
        )
        return BirthLogRead.model_validate(log)

    async def list_birth_logs(self, patient_id: uuid.UUID) -> list[BirthLogRead]:
        result = await self._db.execute(
            select(BirthLog).where(BirthLog.patient_id == patient_id)
        )
        return [BirthLogRead.model_validate(r) for r in result.scalars().all()]

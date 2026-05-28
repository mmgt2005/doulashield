from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import AuditLogger
from app.core.encryption import decrypt_field, encrypt_field
from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientRead, PatientReadWithMedicaidId, PatientUpdate


def _to_read(patient: Patient) -> PatientRead:
    return PatientRead(
        id=patient.id,
        provider_id=patient.provider_id,
        name=decrypt_field(patient.name_encrypted),
        mco=patient.mco,
        medicaid_card_image_path=patient.medicaid_card_image_path,
        is_active=patient.is_active,
        created_at=patient.created_at,
        updated_at=patient.updated_at,
    )


class PatientService:
    def __init__(self, db: AsyncSession, audit: AuditLogger) -> None:
        self._db = db
        self._audit = audit

    async def create(
        self, data: PatientCreate, provider_id: uuid.UUID, ip: str, user_agent: str
    ) -> PatientRead:
        patient = Patient(
            provider_id=provider_id,
            name_encrypted=encrypt_field(data.name),
            medicaid_id_encrypted=encrypt_field(data.medicaid_id),
            mco=data.mco,
            medicaid_card_image_path=data.medicaid_card_image_path,
        )
        self._db.add(patient)
        await self._db.commit()
        await self._db.refresh(patient)

        await self._audit.log(
            action="CREATE",
            resource_type="patient",
            resource_id=patient.id,
            ip_address=ip,
            user_agent=user_agent,
            user_id=provider_id,
        )
        return _to_read(patient)

    async def get(
        self, patient_id: uuid.UUID, requesting_user_id: uuid.UUID, ip: str, user_agent: str
    ) -> PatientRead:
        result = await self._db.execute(select(Patient).where(Patient.id == patient_id))
        patient = result.scalar_one_or_none()
        if not patient or not patient.is_active:
            raise ValueError("Patient not found")

        await self._audit.log(
            action="READ",
            resource_type="patient",
            resource_id=patient_id,
            ip_address=ip,
            user_agent=user_agent,
            user_id=requesting_user_id,
        )
        return _to_read(patient)

    async def get_medicaid_id(
        self, patient_id: uuid.UUID, requesting_user_id: uuid.UUID, ip: str, user_agent: str
    ) -> str:
        """Privileged endpoint — has its own audit log action for HIPAA minimum-necessary tracking."""
        result = await self._db.execute(select(Patient).where(Patient.id == patient_id))
        patient = result.scalar_one_or_none()
        if not patient:
            raise ValueError("Patient not found")

        await self._audit.log(
            action="READ_MEDICAID_ID",
            resource_type="patient",
            resource_id=patient_id,
            ip_address=ip,
            user_agent=user_agent,
            user_id=requesting_user_id,
        )
        return decrypt_field(patient.medicaid_id_encrypted)

    async def list_for_provider(
        self, provider_id: uuid.UUID
    ) -> list[PatientRead]:
        result = await self._db.execute(
            select(Patient).where(Patient.provider_id == provider_id, Patient.is_active == True)
        )
        return [_to_read(p) for p in result.scalars().all()]

    async def list_all(self) -> list[PatientRead]:
        result = await self._db.execute(select(Patient).where(Patient.is_active == True))
        return [_to_read(p) for p in result.scalars().all()]

    async def update(
        self,
        patient_id: uuid.UUID,
        data: PatientUpdate,
        requesting_user_id: uuid.UUID,
        ip: str,
        user_agent: str,
    ) -> PatientRead:
        result = await self._db.execute(select(Patient).where(Patient.id == patient_id))
        patient = result.scalar_one_or_none()
        if not patient or not patient.is_active:
            raise ValueError("Patient not found")

        if data.name is not None:
            patient.name_encrypted = encrypt_field(data.name)
        if data.mco is not None:
            patient.mco = data.mco

        await self._db.commit()
        await self._db.refresh(patient)

        await self._audit.log(
            action="UPDATE",
            resource_type="patient",
            resource_id=patient_id,
            ip_address=ip,
            user_agent=user_agent,
            user_id=requesting_user_id,
        )
        return _to_read(patient)

    async def deactivate(
        self,
        patient_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        requesting_user_role: str,
        ip: str,
        user_agent: str,
    ) -> None:
        if requesting_user_role != "admin":
            raise PermissionError("Only admins can deactivate patient records")

        result = await self._db.execute(select(Patient).where(Patient.id == patient_id))
        patient = result.scalar_one_or_none()
        if not patient:
            raise ValueError("Patient not found")

        patient.is_active = False
        await self._db.commit()

        await self._audit.log(
            action="SOFT_DELETE",
            resource_type="patient",
            resource_id=patient_id,
            ip_address=ip,
            user_agent=user_agent,
            user_id=requesting_user_id,
        )

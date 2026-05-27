from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import AuditLogger
from app.models.soap_note import SOAPNote
from app.schemas.soap_note import SOAPNoteCreate, SOAPNoteRead, SOAPNoteUpdate


class NoteService:
    def __init__(self, db: AsyncSession, audit: AuditLogger) -> None:
        self._db = db
        self._audit = audit

    async def create(
        self,
        patient_id: uuid.UUID,
        provider_id: uuid.UUID,
        data: SOAPNoteCreate,
        ip: str,
        user_agent: str,
    ) -> SOAPNoteRead:
        note = SOAPNote(
            patient_id=patient_id,
            provider_id=provider_id,
            **data.model_dump(),
        )
        self._db.add(note)
        await self._db.commit()
        await self._db.refresh(note)

        await self._audit.log(
            action="CREATE",
            resource_type="soap_note",
            resource_id=note.id,
            ip_address=ip,
            user_agent=user_agent,
            user_id=provider_id,
        )
        return SOAPNoteRead.model_validate(note)

    async def list_for_patient(self, patient_id: uuid.UUID) -> list[SOAPNoteRead]:
        result = await self._db.execute(
            select(SOAPNote).where(SOAPNote.patient_id == patient_id)
        )
        return [SOAPNoteRead.model_validate(n) for n in result.scalars().all()]

    async def update(
        self,
        note_id: uuid.UUID,
        data: SOAPNoteUpdate,
        requesting_user_id: uuid.UUID,
        ip: str,
        user_agent: str,
    ) -> SOAPNoteRead:
        result = await self._db.execute(select(SOAPNote).where(SOAPNote.id == note_id))
        note = result.scalar_one_or_none()
        if not note:
            raise ValueError("Note not found")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(note, field, value)

        await self._db.commit()
        await self._db.refresh(note)

        await self._audit.log(
            action="UPDATE",
            resource_type="soap_note",
            resource_id=note_id,
            ip_address=ip,
            user_agent=user_agent,
            user_id=requesting_user_id,
        )
        return SOAPNoteRead.model_validate(note)

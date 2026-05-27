import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditLogger
from app.dependencies import (
    CurrentUser,
    get_audit,
    get_client_ip,
    get_current_user,
    get_db,
    get_user_agent,
)
from app.schemas.soap_note import SOAPNoteCreate, SOAPNoteRead, SOAPNoteUpdate
from app.services.note_service import NoteService

router = APIRouter(prefix="/patients/{patient_id}/soap-notes", tags=["soap-notes"])


@router.post("", response_model=SOAPNoteRead, status_code=status.HTTP_201_CREATED)
async def create_note(
    request: Request,
    patient_id: uuid.UUID,
    body: SOAPNoteCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> SOAPNoteRead:
    return await NoteService(db, audit).create(
        patient_id, current_user.id, body, get_client_ip(request), get_user_agent(request)
    )


@router.get("", response_model=list[SOAPNoteRead])
async def list_notes(
    patient_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> list[SOAPNoteRead]:
    return await NoteService(db, audit).list_for_patient(patient_id)


@router.patch("/{note_id}", response_model=SOAPNoteRead)
async def update_note(
    request: Request,
    patient_id: uuid.UUID,
    note_id: uuid.UUID,
    body: SOAPNoteUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> SOAPNoteRead:
    try:
        return await NoteService(db, audit).update(
            note_id, body, current_user.id, get_client_ip(request), get_user_agent(request)
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditLogger
from app.dependencies import CurrentUser, get_audit, get_client_ip, get_current_user, get_db, get_user_agent
from app.models.visit import VisitType
from app.schemas.visit import VisitCreate, VisitRead
from app.services.visit_service import VisitService

router = APIRouter(prefix="/patients/{patient_id}/visits", tags=["visits"])


@router.get("", response_model=list[VisitRead])
async def list_visits(
    patient_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> list[VisitRead]:
    return await VisitService(db, audit).list_for_patient(patient_id)


@router.get("/{visit_type}", response_model=VisitRead)
async def get_visit(
    patient_id: uuid.UUID,
    visit_type: VisitType,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> VisitRead:
    visit = await VisitService(db, audit).get_by_type(patient_id, visit_type)
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found.")
    return visit


@router.put("/{visit_type}", response_model=VisitRead)
async def upsert_visit(
    request: Request,
    patient_id: uuid.UUID,
    visit_type: VisitType,
    body: VisitCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> VisitRead:
    return await VisitService(db, audit).upsert(
        patient_id,
        current_user.id,
        visit_type,
        body,
        get_client_ip(request),
        get_user_agent(request),
    )

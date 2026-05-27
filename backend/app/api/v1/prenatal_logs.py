import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
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
from app.schemas.prenatal_log import PrenatalLogCreate, PrenatalLogRead
from app.services.log_service import LogService

router = APIRouter(prefix="/patients/{patient_id}/prenatal-logs", tags=["prenatal-logs"])


@router.post("", response_model=PrenatalLogRead, status_code=status.HTTP_201_CREATED)
async def create_log(
    request: Request,
    patient_id: uuid.UUID,
    body: PrenatalLogCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> PrenatalLogRead:
    return await LogService(db, audit).create_prenatal_log(
        patient_id, current_user.id, body, get_client_ip(request), get_user_agent(request)
    )


@router.get("", response_model=list[PrenatalLogRead])
async def list_logs(
    patient_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> list[PrenatalLogRead]:
    return await LogService(db, audit).list_prenatal_logs(patient_id)

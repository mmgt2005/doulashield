import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditLogger
from app.dependencies import CurrentUser, get_audit, get_client_ip, get_current_user, get_db, get_user_agent
from app.schemas.prior_auth import PriorAuthCreate, PriorAuthRead
from app.services.prior_auth_service import PriorAuthService

router = APIRouter(tags=["prior-auth"])


def _svc(db: AsyncSession, audit: AuditLogger) -> PriorAuthService:
    return PriorAuthService(db, audit)


@router.post("/patients/{patient_id}/prior-authorizations", response_model=PriorAuthRead, status_code=status.HTTP_201_CREATED)
async def submit_prior_auth(
    request: Request,
    patient_id: uuid.UUID,
    body: PriorAuthCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> PriorAuthRead:
    try:
        return await _svc(db, audit).submit_prior_auth(
            patient_id, current_user.id, body, get_client_ip(request), get_user_agent(request)
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/patients/{patient_id}/prior-authorizations", response_model=list[PriorAuthRead])
async def list_prior_auths(
    patient_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> list[PriorAuthRead]:
    return await _svc(db, audit).list_prior_auths(current_user.id, patient_id)


@router.post("/prior-authorizations/{auth_id}/status-check", response_model=PriorAuthRead)
async def check_auth_status(
    request: Request,
    auth_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> PriorAuthRead:
    try:
        return await _svc(db, audit).check_auth_status(
            auth_id, current_user.id, get_client_ip(request), get_user_agent(request)
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

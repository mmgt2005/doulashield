import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditLogger
from app.dependencies import CurrentUser, get_audit, get_client_ip, get_current_user, get_db, get_user_agent
from app.schemas.claim import ClaimCreate, ClaimRead
from app.services.claims_service import ClaimsService

router = APIRouter(tags=["claims"])


def _svc(db: AsyncSession, audit: AuditLogger) -> ClaimsService:
    return ClaimsService(db, audit)


@router.post("/patients/{patient_id}/claims", response_model=ClaimRead, status_code=status.HTTP_201_CREATED)
async def submit_claim(
    request: Request,
    patient_id: uuid.UUID,
    body: ClaimCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> ClaimRead:
    try:
        return await _svc(db, audit).submit_claim(
            patient_id, current_user.id, body, get_client_ip(request), get_user_agent(request)
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/patients/{patient_id}/claims", response_model=list[ClaimRead])
async def list_claims(
    patient_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> list[ClaimRead]:
    return await _svc(db, audit).list_claims(current_user.id, patient_id)


@router.post("/claims/{claim_id}/status-check", response_model=ClaimRead)
async def check_claim_status(
    request: Request,
    claim_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> ClaimRead:
    try:
        return await _svc(db, audit).check_claim_status(
            claim_id, current_user.id, get_client_ip(request), get_user_agent(request)
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

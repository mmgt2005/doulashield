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
    require_admin,
)
from app.schemas.patient import PatientCreate, PatientRead, PatientReadWithMedicaidId, PatientUpdate, PatientSearch
from app.services.eligibility_service import EligibilityService
from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients", tags=["patients"])


def _svc(db: AsyncSession, audit: AuditLogger) -> PatientService:
    return PatientService(db, audit)


@router.post("", response_model=PatientRead, status_code=status.HTTP_201_CREATED)
async def create_patient(
    request: Request,
    body: PatientCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> PatientRead:
    return await _svc(db, audit).create(
        body, current_user.id, get_client_ip(request), get_user_agent(request)
    )


@router.post("/search", response_model=list[PatientRead])
async def search_patients(
    body: PatientSearch,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> list[PatientRead]:
    """Search via POST to keep query terms out of URL/access logs."""
    patients = await _svc(db, audit).list_for_provider(current_user.id)

    query = body.query.lower()
    return [p for p in patients if query in p.name.lower() or (p.mco and query in p.mco.lower())]


@router.get("", response_model=list[PatientRead])
async def list_patients(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> list[PatientRead]:
    return await _svc(db, audit).list_for_provider(current_user.id)


@router.get("/{patient_id}", response_model=PatientRead)
async def get_patient(
    request: Request,
    patient_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> PatientRead:
    try:
        return await _svc(db, audit).get(
            patient_id, current_user.id, get_client_ip(request), get_user_agent(request)
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.get("/{patient_id}/medicaid-id", response_model=PatientReadWithMedicaidId)
async def get_medicaid_id(
    request: Request,
    patient_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> PatientReadWithMedicaidId:
    """Admin-only. Generates a separate audit log entry per HIPAA minimum-necessary principle."""
    try:
        patient = await _svc(db, audit).get(
            patient_id, current_user.id, get_client_ip(request), get_user_agent(request)
        )
        medicaid_id = await _svc(db, audit).get_medicaid_id(
            patient_id, current_user.id, get_client_ip(request), get_user_agent(request)
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    return PatientReadWithMedicaidId(**patient.model_dump(), medicaid_id=medicaid_id)


@router.patch("/{patient_id}", response_model=PatientRead)
async def update_patient(
    request: Request,
    patient_id: uuid.UUID,
    body: PatientUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> PatientRead:
    try:
        return await _svc(db, audit).update(
            patient_id, body, current_user.id, get_client_ip(request), get_user_agent(request)
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.post("/{patient_id}/eligibility-check")
async def check_eligibility(
    request: Request,
    patient_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> dict:
    try:
        return await EligibilityService(db, audit).check_eligibility(
            patient_id, current_user.id, get_client_ip(request), get_user_agent(request)
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{patient_id}/deactivate", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_patient(
    request: Request,
    patient_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> None:
    try:
        await _svc(db, audit).deactivate(
            patient_id,
            current_user.id,
            current_user.role,
            get_client_ip(request),
            get_user_agent(request),
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

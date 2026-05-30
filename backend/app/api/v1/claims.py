import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import AuditLogger
from app.core.encryption import decrypt_field
from app.dependencies import CurrentUser, get_audit, get_client_ip, get_current_user, get_db, get_user_agent
from app.models.patient import Patient
from app.models.user import User
from app.models.visit import Visit
from app.schemas.claim import ClaimCreate, ClaimRead
from app.services import cms1500_service
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


@router.get("/patients/{patient_id}/visits/{visit_type}/cms1500.pdf")
async def download_cms1500(
    request: Request,
    patient_id: uuid.UUID,
    visit_type: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> Response:
    patient_result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = patient_result.scalar_one_or_none()
    if not patient or not patient.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    user_result = await db.execute(select(User).where(User.id == current_user.id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    visit_result = await db.execute(
        select(Visit).where(Visit.patient_id == patient_id, Visit.visit_type == visit_type)
    )
    visit = visit_result.scalar_one_or_none()

    from datetime import date as date_type
    svc_date: date_type | None = None
    if visit and visit.visit_date:
        svc_date = visit.visit_date
    elif visit and visit.visit_started_at:
        svc_date = visit.visit_started_at.date()

    location_type = visit.location_type if visit else None

    try:
        pdf_bytes = cms1500_service.generate_pdf(
            patient_data={
                "name": decrypt_field(patient.name_encrypted),
                "medicaid_id": decrypt_field(patient.medicaid_id_encrypted),
                "date_of_birth": patient.date_of_birth,
                "gender": patient.gender,
                "address": patient.address or "",
                "referring_provider_npi": patient.referring_provider_npi or "",
            },
            visit_data={
                "visit_type": visit_type,
                "visit_date": svc_date,
                "location_type": location_type,
                "prior_auth_number": visit.prior_auth_number if visit else None,
            },
            provider_data={
                "npi": user.npi or "",
                "full_name": user.full_name or "",
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    await audit.log(
        action="GENERATE_CMS1500",
        resource_type="patient",
        resource_id=patient_id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        user_id=current_user.id,
        extra_context={"visit_type": visit_type},
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="cms1500_{visit_type}.pdf"'},
    )


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

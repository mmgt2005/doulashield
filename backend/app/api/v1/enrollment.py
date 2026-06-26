"""Admin-managed PCB enrollment service API."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import AuditLogger
from app.dependencies import CurrentUser, get_audit, get_db, require_admin
from app.models.enrollment import EnrollmentDocument, EnrollmentService, EnrollmentTask
from app.models.user import User
from app.schemas.enrollment import (
    CompleteMcoContractingRequest,
    CompleteEnrollmentRequest,
    CompletePcbRequest,
    EnrollmentDocumentRead,
    EnrollmentServiceCreate,
    EnrollmentServiceDetail,
    EnrollmentServiceRead,
    EnrollmentTaskRead,
    EnrollmentTaskUpdate,
)

router = APIRouter(tags=["enrollment"], prefix="/admin/enrollment")

# ── Task seed definitions ──────────────────────────────────────────────────────

_TASK_SEEDS: dict[str, list[dict]] = {
    "education_training": [
        {
            "task_key": "pcb_training_hours",
            "required_pathway": "education_training",
            "label": "Training Certificate(s) — 24 Hours Minimum",
            "description": (
                "Upload training program certificate(s). Total documented hours across all "
                "certificates must be ≥ 24. All hours must relate to perinatal doula knowledge "
                "areas (birth support, postpartum care, breastfeeding, perinatal mood disorders, etc.)."
            ),
            "sort_order": 1,
        },
        {
            "task_key": "pcb_hipaa_cert",
            "required_pathway": "education_training",
            "label": "HIPAA/Confidentiality Training Certificate — 1 Hour Minimum",
            "description": (
                "Upload certificate showing ≥ 1 hour of HIPAA or client confidentiality training. "
                "This can be a standalone online course or a HIPAA module within their training program "
                "if hours are explicitly listed."
            ),
            "sort_order": 2,
        },
        {
            "task_key": "pcb_cpr_cert",
            "required_pathway": "all",
            "label": "CPR Certification — Adult + Infant",
            "description": (
                "Upload current, unexpired CPR certificate explicitly covering adult and infant "
                "competencies. Accepted: AHA BLS, American Red Cross CPR/AED for Professional Rescuers. "
                "Online-only certifications without hands-on skills are NOT accepted."
            ),
            "sort_order": 3,
        },
        {
            "task_key": "pcb_client_eval_1",
            "required_pathway": "all",
            "label": "Client Evaluation #1",
            "description": (
                "Upload completed PCB client evaluation form, signed by the family. "
                "Download the official form at pacertboard.org/doula."
            ),
            "sort_order": 4,
        },
        {
            "task_key": "pcb_client_eval_2",
            "required_pathway": "all",
            "label": "Client Evaluation #2",
            "description": (
                "Upload completed PCB client evaluation form, signed by the family. "
                "Download the official form at pacertboard.org/doula."
            ),
            "sort_order": 5,
        },
        {
            "task_key": "pcb_client_eval_3",
            "required_pathway": "all",
            "label": "Client Evaluation #3",
            "description": (
                "Upload completed PCB client evaluation form, signed by the family. "
                "Download the official form at pacertboard.org/doula."
            ),
            "sort_order": 6,
        },
    ],
    "experienced": [
        {
            "task_key": "pcb_active_practice",
            "required_pathway": "experienced",
            "label": "Proof of Active Practice",
            "description": (
                "Upload documentation confirming the provider is currently working as a doula. "
                "Acceptable: agency letter confirming contractor status, active doula directory listing "
                "(screenshot with URL), business registration, or signed client statement."
            ),
            "sort_order": 1,
        },
        {
            "task_key": "pcb_cpr_cert",
            "required_pathway": "all",
            "label": "CPR Certification — Adult + Infant",
            "description": (
                "Upload current, unexpired CPR certificate explicitly covering adult and infant "
                "competencies. Accepted: AHA BLS, American Red Cross CPR/AED for Professional Rescuers. "
                "Online-only certifications without hands-on skills are NOT accepted."
            ),
            "sort_order": 2,
        },
        {
            "task_key": "pcb_client_eval_1",
            "required_pathway": "all",
            "label": "Client Evaluation #1 (within last year)",
            "description": (
                "Upload completed PCB client evaluation form, signed by the family. "
                "Must be from a family served within the last 12 months."
            ),
            "sort_order": 3,
        },
        {
            "task_key": "pcb_client_eval_2",
            "required_pathway": "all",
            "label": "Client Evaluation #2 (within last year)",
            "description": (
                "Upload completed PCB client evaluation form, signed by the family. "
                "Must be from a family served within the last 12 months."
            ),
            "sort_order": 4,
        },
        {
            "task_key": "pcb_client_eval_3",
            "required_pathway": "all",
            "label": "Client Evaluation #3 (within last year)",
            "description": (
                "Upload completed PCB client evaluation form, signed by the family. "
                "Must be from a family served within the last 12 months."
            ),
            "sort_order": 5,
        },
        {
            "task_key": "pcb_ref_letter_1",
            "required_pathway": "experienced",
            "label": "Letter of Recommendation #1 (within last year)",
            "description": (
                "Upload signed letter of recommendation from a family served within the last 12 months. "
                "Free-form letter, not a PCB form. Must be signed and dated by the client."
            ),
            "sort_order": 6,
        },
        {
            "task_key": "pcb_ref_letter_2",
            "required_pathway": "experienced",
            "label": "Letter of Recommendation #2 (within last year)",
            "description": (
                "Upload signed letter of recommendation from a family served within the last 12 months."
            ),
            "sort_order": 7,
        },
        {
            "task_key": "pcb_ref_letter_3",
            "required_pathway": "experienced",
            "label": "Letter of Recommendation #3 (within last year)",
            "description": (
                "Upload signed letter of recommendation from a family served within the last 12 months."
            ),
            "sort_order": 8,
        },
    ],
}


_STAGE2_TASKS: list[dict] = [
    {
        "task_key": "w9",
        "required_pathway": "all",
        "label": "W-9 Form",
        "description": (
            "Upload a completed, signed IRS Form W-9 for the provider. "
            "The legal name and TIN must match what will be submitted to PROMISe™ and CAQH. "
            "If the provider operates as a sole proprietor, use their SSN; if they have an EIN, use that."
        ),
        "sort_order": 1,
    },
    {
        "task_key": "govt_id",
        "required_pathway": "all",
        "label": "Government-Issued Photo ID",
        "description": (
            "Upload a clear copy of the provider's current, unexpired government-issued photo ID. "
            "Acceptable: driver's license, state ID, or passport. "
            "Both front and back of a driver's license or state ID must be included."
        ),
        "sort_order": 2,
    },
    {
        "task_key": "liability_face_sheet",
        "required_pathway": "all",
        "label": "Liability Insurance Face Sheet",
        "description": (
            "Upload the declarations page (face sheet) from the provider's professional liability "
            "insurance policy. Must show: insured name, policy number, coverage dates, and minimum "
            "limits of $1,000,000 per occurrence / $3,000,000 aggregate. "
            "DoulaShield's group policy covers all enrolled providers — upload that face sheet "
            "once confirmed by the agency."
        ),
        "sort_order": 3,
    },
    {
        "task_key": "promise_type13",
        "required_pathway": "all",
        "label": "PROMISe™ Type 13 Application (Medicaid)",
        "description": (
            "Upload confirmation of PROMISe™ Type 13 (Medicaid) provider enrollment submission. "
            "This can be a screenshot of the online application confirmation page or the ATN "
            "(Application Tracking Number) email from DHS. "
            "The provider's PCB certification number should be entered in the 'Credentials' section."
        ),
        "sort_order": 4,
    },
    {
        "task_key": "promise_type130",
        "required_pathway": "all",
        "label": "PROMISe™ Type 130 Application (CHIP)",
        "description": (
            "Upload confirmation of PROMISe™ Type 130 (CHIP) provider enrollment submission. "
            "Separate application from Type 13. Required to bill CHIP MCOs (Keystone First CHIP, "
            "UPMC for You CHIP, etc.). Process is the same as Type 13 but select Type 130 in the "
            "PROMISe™ portal."
        ),
        "sort_order": 5,
    },
    {
        "task_key": "caqh_pv_enrollment",
        "required_pathway": "all",
        "label": "CAQH ProView Enrollment",
        "description": (
            "Upload a screenshot or PDF confirming the provider's CAQH ProView profile is complete "
            "and attested. Record the CAQH ID in the notes field below. "
            "All MCOs require an active, attested CAQH ProView profile before processing credentialing. "
            "Attestation must be renewed every 120 days."
        ),
        "sort_order": 6,
    },
]

_STAGE3_TASKS: list[dict] = [
    {
        "task_key": "mco_work_history",
        "required_pathway": "all",
        "label": "5-Year Work History",
        "description": (
            "Upload a document listing the provider's work history for the past 5 years. "
            "Include: employer/agency name, address, dates of employment, and reason for leaving. "
            "Gaps of 6 months or more must be explained. "
            "This is submitted with each MCO credentialing application."
        ),
        "sort_order": 1,
    },
    {
        "task_key": "mco_resume_cv",
        "required_pathway": "all",
        "label": "Resume / CV",
        "description": (
            "Upload the provider's current resume or curriculum vitae. "
            "Should highlight doula experience, training certifications, and any clinical or "
            "perinatal health-related experience. Several MCOs request this as part of their "
            "credentialing packet."
        ),
        "sort_order": 2,
    },
    {
        "task_key": "mco_amerihealth",
        "required_pathway": "all",
        "label": "AmeriHealth Caritas — Application + LOI",
        "description": (
            "Upload the completed AmeriHealth Caritas PA credentialing application and Letter of "
            "Intent (LOI). The LOI should state the provider's intent to contract as a doula "
            "under the agency's billing NPI. Record the application reference number and submission "
            "date in notes. Record the contract signing date in the Contract Date field when received."
        ),
        "sort_order": 3,
    },
    {
        "task_key": "mco_keystone",
        "required_pathway": "all",
        "label": "Keystone First — Application + LOI",
        "description": (
            "Upload the completed Keystone First credentialing application and LOI. "
            "Record reference number, submission date, and contract date in notes/task data."
        ),
        "sort_order": 4,
    },
    {
        "task_key": "mco_upmc",
        "required_pathway": "all",
        "label": "UPMC For You — Application + LOI",
        "description": (
            "Upload the completed UPMC For You credentialing application and LOI. "
            "Record reference number, submission date, and contract date in notes/task data."
        ),
        "sort_order": 5,
    },
    {
        "task_key": "mco_geisinger",
        "required_pathway": "all",
        "label": "Geisinger Health Plan — Application + LOI",
        "description": (
            "Upload the completed Geisinger Health Plan credentialing application and LOI. "
            "Record reference number, submission date, and contract date in notes/task data."
        ),
        "sort_order": 6,
    },
    {
        "task_key": "mco_highmark",
        "required_pathway": "all",
        "label": "Highmark Wholecare — Application + LOI",
        "description": (
            "Upload the completed Highmark Wholecare credentialing application and LOI. "
            "Record reference number, submission date, and contract date in notes/task data."
        ),
        "sort_order": 7,
    },
    {
        "task_key": "mco_uhc",
        "required_pathway": "all",
        "label": "UnitedHealthcare Community Plan — Application + LOI",
        "description": (
            "Upload the completed UnitedHealthcare Community Plan credentialing application and LOI. "
            "Record reference number, submission date, and contract date in notes/task data."
        ),
        "sort_order": 8,
    },
    {
        "task_key": "mco_aetna",
        "required_pathway": "all",
        "label": "Aetna Better Health — Application + LOI",
        "description": (
            "Upload the completed Aetna Better Health PA credentialing application and LOI. "
            "Record reference number, submission date, and contract date in notes/task data."
        ),
        "sort_order": 9,
    },
    {
        "task_key": "mco_hpplans",
        "required_pathway": "all",
        "label": "Health Partners Plans — Application + LOI",
        "description": (
            "Upload the completed Health Partners Plans credentialing application and LOI. "
            "Record reference number, submission date, and contract date in notes/task data."
        ),
        "sort_order": 10,
    },
]


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_service_or_404(service_id: uuid.UUID, db: AsyncSession) -> EnrollmentService:
    result = await db.execute(select(EnrollmentService).where(EnrollmentService.id == service_id))
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrollment service not found")
    return service


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/services", response_model=list[EnrollmentServiceRead])
async def list_enrollment_services(
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[EnrollmentServiceRead]:
    result = await db.execute(
        select(EnrollmentService).order_by(EnrollmentService.created_at.desc())
    )
    services = result.scalars().all()
    return [EnrollmentServiceRead.model_validate(s) for s in services]


@router.post("/services", response_model=EnrollmentServiceDetail, status_code=status.HTTP_201_CREATED)
async def create_enrollment_service(
    body: EnrollmentServiceCreate,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> EnrollmentServiceDetail:
    provider_result = await db.execute(select(User).where(User.id == body.provider_id))
    provider = provider_result.scalar_one_or_none()
    if not provider or provider.role != "provider":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")

    stage = body.stage or "pcb"

    if stage == "pcb":
        if not body.pcb_pathway:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="pcb_pathway is required for PCB enrollment services.",
            )

    if stage == "enrollment":
        if not provider.pcb_last_certified_on:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Stage 1 (PCB certification) must be complete before starting Stage 2 enrollment.",
            )

    if stage == "mco_contracting":
        stage2_result = await db.execute(
            select(EnrollmentService).where(
                EnrollmentService.provider_id == body.provider_id,
                EnrollmentService.stage == "enrollment",
                EnrollmentService.status == "complete",
            )
        )
        if not stage2_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Stage 2 (enrollment) must be complete before starting MCO contracting.",
            )

    service = EnrollmentService(
        provider_id=body.provider_id,
        created_by=current_user.id,
        stage=stage,
        pcb_pathway=body.pcb_pathway if stage == "pcb" else None,
        status="in_progress",
        intake_data=body.intake_data,
    )
    db.add(service)
    await db.flush()

    if stage == "pcb":
        task_seeds = _TASK_SEEDS.get(body.pcb_pathway, [])
    elif stage == "enrollment":
        task_seeds = _STAGE2_TASKS
    else:
        task_seeds = _STAGE3_TASKS

    tasks: list[EnrollmentTask] = []
    for seed in task_seeds:
        task = EnrollmentTask(
            service_id=service.id,
            task_key=seed["task_key"],
            required_pathway=seed["required_pathway"],
            label=seed["label"],
            description=seed["description"],
            sort_order=seed["sort_order"],
            status="not_started",
        )
        db.add(task)
        tasks.append(task)

    await db.commit()
    await db.refresh(service)
    for t in tasks:
        await db.refresh(t)

    await audit.log(
        action="ENROLLMENT_SERVICE_CREATED",
        user_id=current_user.id,
        details={
            "service_id": str(service.id),
            "provider_id": str(body.provider_id),
            "stage": stage,
            "pathway": body.pcb_pathway,
        },
        request=request,
    )

    return EnrollmentServiceDetail(
        service=EnrollmentServiceRead.model_validate(service),
        tasks=[EnrollmentTaskRead.model_validate(t) for t in tasks],
        documents=[],
        provider_email=provider.email,
        provider_name=provider.full_name,
    )


@router.get("/services/{service_id}", response_model=EnrollmentServiceDetail)
async def get_enrollment_service(
    service_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EnrollmentServiceDetail:
    service = await _get_service_or_404(service_id, db)

    tasks_result = await db.execute(
        select(EnrollmentTask)
        .where(EnrollmentTask.service_id == service_id)
        .order_by(EnrollmentTask.sort_order)
    )
    tasks = tasks_result.scalars().all()

    docs_result = await db.execute(
        select(EnrollmentDocument)
        .where(EnrollmentDocument.service_id == service_id)
        .order_by(EnrollmentDocument.created_at)
    )
    docs = docs_result.scalars().all()

    provider_result = await db.execute(select(User).where(User.id == service.provider_id))
    provider = provider_result.scalar_one_or_none()

    return EnrollmentServiceDetail(
        service=EnrollmentServiceRead.model_validate(service),
        tasks=[EnrollmentTaskRead.model_validate(t) for t in tasks],
        documents=[EnrollmentDocumentRead.model_validate(d) for d in docs],
        provider_email=provider.email if provider else None,
        provider_name=provider.full_name if provider else None,
    )


@router.patch("/tasks/{task_id}", response_model=EnrollmentTaskRead)
async def update_enrollment_task(
    task_id: uuid.UUID,
    body: EnrollmentTaskUpdate,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EnrollmentTaskRead:
    result = await db.execute(select(EnrollmentTask).where(EnrollmentTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Training hours validation
    if body.status == "complete" and task.task_key == "pcb_training_hours":
        hours = (body.task_data or {}).get("hours") or (task.task_data or {}).get("hours", 0)
        if int(hours) < 24:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Training hours must be ≥ 24 to complete this task (currently {hours}).",
            )
    if body.status == "complete" and task.task_key == "pcb_hipaa_cert":
        hours = (body.task_data or {}).get("hours") or (task.task_data or {}).get("hours", 0)
        if int(hours) < 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="HIPAA training hours must be ≥ 1 to complete this task.",
            )

    if body.status is not None:
        task.status = body.status
        if body.status == "complete":
            task.completed_at = datetime.now(timezone.utc)
        elif task.completed_at is not None:
            task.completed_at = None
    if body.notes is not None:
        task.notes = body.notes
    if body.task_data is not None:
        task.task_data = body.task_data

    await db.commit()
    await db.refresh(task)
    return EnrollmentTaskRead.model_validate(task)


@router.post("/services/{service_id}/complete-pcb", response_model=EnrollmentServiceRead)
async def complete_pcb_certification(
    service_id: uuid.UUID,
    body: CompletePcbRequest,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> EnrollmentServiceRead:
    service = await _get_service_or_404(service_id, db)

    service.status = "complete"
    service.pcb_cert_date = body.cert_date

    provider_result = await db.execute(select(User).where(User.id == service.provider_id))
    provider = provider_result.scalar_one_or_none()
    if provider:
        provider.pcb_last_certified_on = body.cert_date

    await db.commit()
    await db.refresh(service)

    await audit.log(
        action="PCB_CERTIFICATION_COMPLETE",
        user_id=current_user.id,
        details={
            "service_id": str(service_id),
            "provider_id": str(service.provider_id),
            "cert_date": str(body.cert_date),
        },
        request=request,
    )

    return EnrollmentServiceRead.model_validate(service)


@router.post("/services/{service_id}/complete-enrollment", response_model=EnrollmentServiceRead)
async def complete_enrollment(
    service_id: uuid.UUID,
    body: CompleteEnrollmentRequest,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> EnrollmentServiceRead:
    service = await _get_service_or_404(service_id, db)
    if service.stage != "enrollment":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This endpoint is only for Stage 2 enrollment services.",
        )

    service.status = "complete"
    intake = dict(service.intake_data or {})
    if body.promise_id:
        intake["promise_id"] = body.promise_id
    if body.caqh_id:
        intake["caqh_id"] = body.caqh_id
    service.intake_data = intake

    provider_result = await db.execute(select(User).where(User.id == service.provider_id))
    provider = provider_result.scalar_one_or_none()
    if provider:
        provider.promise_last_enrolled_on = body.promise_enrolled_on
        if body.liability_insurance_expires_on:
            provider.liability_insurance_expires_on = body.liability_insurance_expires_on

    await db.commit()
    await db.refresh(service)

    await audit.log(
        action="ENROLLMENT_STAGE2_COMPLETE",
        user_id=current_user.id,
        details={
            "service_id": str(service_id),
            "provider_id": str(service.provider_id),
            "promise_enrolled_on": str(body.promise_enrolled_on),
        },
        request=request,
    )

    return EnrollmentServiceRead.model_validate(service)


@router.post("/services/{service_id}/complete-mco-contracting", response_model=EnrollmentServiceRead)
async def complete_mco_contracting(
    service_id: uuid.UUID,
    body: CompleteMcoContractingRequest,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> EnrollmentServiceRead:
    service = await _get_service_or_404(service_id, db)
    if service.stage != "mco_contracting":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This endpoint is only for Stage 3 MCO contracting services.",
        )

    service.status = "complete"
    intake = dict(service.intake_data or {})
    intake["contracted_on"] = str(body.contracted_on)
    service.intake_data = intake

    await db.commit()
    await db.refresh(service)

    await audit.log(
        action="ENROLLMENT_STAGE3_COMPLETE",
        user_id=current_user.id,
        details={
            "service_id": str(service_id),
            "provider_id": str(service.provider_id),
            "contracted_on": str(body.contracted_on),
        },
        request=request,
    )

    return EnrollmentServiceRead.model_validate(service)


@router.post(
    "/services/{service_id}/tasks/{task_id}/documents",
    response_model=EnrollmentDocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_enrollment_document(
    service_id: uuid.UUID,
    task_id: uuid.UUID,
    file: UploadFile,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    document_type: Annotated[str, Form()] = "other",
) -> EnrollmentDocumentRead:
    from app.services.ocr_service import store_image

    _MAX_BYTES = 20 * 1024 * 1024
    _ALLOWED_TYPES = {"image/jpeg", "image/png", "application/pdf"}

    content_type = file.content_type or ""
    if content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG, or PDF files are accepted.",
        )

    content_bytes = await file.read()
    if len(content_bytes) > _MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File must be under 20 MB.",
        )

    service = await _get_service_or_404(service_id, db)

    task_result = await db.execute(
        select(EnrollmentTask).where(
            EnrollmentTask.id == task_id,
            EnrollmentTask.service_id == service_id,
        )
    )
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    file_path = await store_image(
        content_bytes, content_type, None, current_user.id, f"enrollment-doc-{service_id}"
    )

    doc = EnrollmentDocument(
        service_id=service_id,
        task_id=task_id,
        uploaded_by=current_user.id,
        file_path=file_path,
        file_name=file.filename or "document",
        document_type=document_type,
    )
    db.add(doc)

    if task.status == "not_started":
        task.status = "in_progress"

    await db.commit()
    await db.refresh(doc)
    return EnrollmentDocumentRead.model_validate(doc)


@router.get("/services/{service_id}/documents/{doc_id}/url")
async def get_enrollment_document_url(
    service_id: uuid.UUID,
    doc_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    from app.services.ocr_service import get_signed_url

    doc_result = await db.execute(
        select(EnrollmentDocument).where(
            EnrollmentDocument.id == doc_id,
            EnrollmentDocument.service_id == service_id,
        )
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    url = await get_signed_url(doc.file_path, expires_in=300)
    return {"url": url, "file_name": doc.file_name}

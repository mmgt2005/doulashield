"""Billing-admin self-service enrollment endpoints.

All routes require:
  1. billing_admin role (via require_billing_enrollment_tier dependency chain)
  2. enrollment_tier_enabled on the managed BillingProvider
  3. Any provider / service / task touched must belong to that BillingProvider
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import AuditLogger
from app.dependencies import (
    CurrentUser,
    get_audit,
    get_client_ip,
    get_current_user,
    get_db,
    get_managed_billing_provider,
    get_user_agent,
    require_billing_admin,
    require_billing_enrollment_tier,
)
from app.models.billing_provider import BillingProvider
from app.models.enrollment import EnrollmentDocument, EnrollmentService, EnrollmentTask
from app.models.user import User
from app.schemas.enrollment import (
    CompleteMcoContractingRequest,
    CompleteEnrollmentRequest,
    CompleteNppesRequest,
    CompletePcbRequest,
    EnrollmentDocumentRead,
    EnrollmentServiceCreate,
    EnrollmentServiceDetail,
    EnrollmentServiceRead,
    EnrollmentTaskRead,
    EnrollmentTaskUpdate,
)

# Re-use the same task seed lists defined in the admin enrollment module
from app.api.v1.enrollment import (
    _NPPES_TASKS,
    _STAGE2_TASKS,
    _STAGE3_TASKS,
    _TASK_SEEDS,
)

router = APIRouter(tags=["billing-admin-enrollment"])


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _assert_provider_in_agency(
    provider_id: uuid.UUID, bp_id: uuid.UUID, db: AsyncSession
) -> User:
    result = await db.execute(
        select(User).where(User.id == provider_id, User.billing_provider_id == bp_id)
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found in your agency")
    return provider


async def _get_service_in_agency(
    service_id: uuid.UUID, bp_id: uuid.UUID, db: AsyncSession
) -> tuple[EnrollmentService, User]:
    svc_result = await db.execute(
        select(EnrollmentService).where(EnrollmentService.id == service_id)
    )
    service = svc_result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrollment service not found")
    provider = await _assert_provider_in_agency(service.provider_id, bp_id, db)
    return service, provider


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/billing-admin/enrollment/services", response_model=list[EnrollmentServiceRead])
async def list_agency_enrollment_services(
    bp: Annotated[BillingProvider, Depends(get_managed_billing_provider)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[EnrollmentServiceRead]:
    """List all enrollment services for every provider in the billing admin's agency."""
    ids_result = await db.execute(select(User.id).where(User.billing_provider_id == bp.id))
    provider_ids = [row[0] for row in ids_result.all()]
    if not provider_ids:
        return []
    result = await db.execute(
        select(EnrollmentService)
        .where(EnrollmentService.provider_id.in_(provider_ids))
        .order_by(EnrollmentService.created_at.desc())
    )
    return [EnrollmentServiceRead.model_validate(s) for s in result.scalars().all()]


@router.post(
    "/billing-admin/enrollment/services",
    response_model=EnrollmentServiceDetail,
    status_code=status.HTTP_201_CREATED,
)
async def create_agency_enrollment_service(
    body: EnrollmentServiceCreate,
    bp: Annotated[BillingProvider, Depends(require_billing_enrollment_tier)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> EnrollmentServiceDetail:
    """Create an enrollment service for one of the agency's providers."""
    provider = await _assert_provider_in_agency(body.provider_id, bp.id, db)
    stage = body.stage or "pcb"

    # Block duplicate active service at the same stage
    _stage_labels = {
        "pcb": "PCB Certification",
        "nppes_setup": "NPPES/NPI Setup",
        "enrollment": "PROMISe Enrollment",
        "mco_contracting": "MCO Contracting",
    }
    dup_result = await db.execute(
        select(EnrollmentService).where(
            EnrollmentService.provider_id == body.provider_id,
            EnrollmentService.stage == stage,
            EnrollmentService.status.in_(["in_progress", "submitted"]),
        )
    )
    if dup_result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"An active {_stage_labels.get(stage, stage)} service already exists for this provider. Complete or cancel it before starting a new one.",
        )

    if stage == "pcb" and not body.pcb_pathway:
        raise HTTPException(status_code=422, detail="pcb_pathway is required for PCB enrollment services.")
    if stage == "nppes_setup" and not provider.pcb_last_certified_on:
        raise HTTPException(status_code=422, detail="PCB Certification must be complete before starting NPPES/NPI Setup.")
    if stage == "enrollment":
        if not provider.pcb_last_certified_on:
            raise HTTPException(status_code=422, detail="Stage 1 (PCB certification) must be complete before starting Stage 2 enrollment.")
        if not provider.npi:
            raise HTTPException(status_code=422, detail="NPPES/NPI Setup must be complete (NPI on file) before starting Stage 2 enrollment.")
    if stage == "mco_contracting":
        existing = await db.execute(
            select(EnrollmentService).where(
                EnrollmentService.provider_id == body.provider_id,
                EnrollmentService.stage == "enrollment",
                EnrollmentService.status == "complete",
            )
        )
        if not existing.scalar_one_or_none():
            raise HTTPException(status_code=422, detail="Stage 2 (enrollment) must be complete before starting MCO contracting.")

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
        task_seeds = _TASK_SEEDS.get(body.pcb_pathway or "", [])
    elif stage == "nppes_setup":
        task_seeds = _NPPES_TASKS
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
        action="BILLING_ADMIN_ENROLLMENT_SERVICE_CREATED",
        user_id=current_user.id,
        resource_type="user",
        resource_id=body.provider_id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        extra_context={
            "service_id": str(service.id),
            "stage": stage,
            "pathway": body.pcb_pathway,
            "billing_provider_id": str(bp.id),
        },
    )

    return EnrollmentServiceDetail(
        service=EnrollmentServiceRead.model_validate(service),
        tasks=[EnrollmentTaskRead.model_validate(t) for t in tasks],
        documents=[],
        provider_email=provider.email,
        provider_name=provider.full_name,
    )


@router.get(
    "/billing-admin/enrollment/services/{service_id}",
    response_model=EnrollmentServiceDetail,
)
async def get_agency_enrollment_service(
    service_id: uuid.UUID,
    bp: Annotated[BillingProvider, Depends(get_managed_billing_provider)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EnrollmentServiceDetail:
    """Fetch tasks and documents for one enrollment service (must belong to this agency)."""
    service, provider = await _get_service_in_agency(service_id, bp.id, db)

    tasks_result = await db.execute(
        select(EnrollmentTask)
        .where(EnrollmentTask.service_id == service_id)
        .order_by(EnrollmentTask.sort_order)
    )
    docs_result = await db.execute(
        select(EnrollmentDocument)
        .where(EnrollmentDocument.service_id == service_id)
        .order_by(EnrollmentDocument.created_at)
    )

    return EnrollmentServiceDetail(
        service=EnrollmentServiceRead.model_validate(service),
        tasks=[EnrollmentTaskRead.model_validate(t) for t in tasks_result.scalars().all()],
        documents=[EnrollmentDocumentRead.model_validate(d) for d in docs_result.scalars().all()],
        provider_email=provider.email,
        provider_name=provider.full_name,
    )


@router.patch(
    "/billing-admin/enrollment/tasks/{task_id}",
    response_model=EnrollmentTaskRead,
)
async def update_agency_enrollment_task(
    task_id: uuid.UUID,
    body: EnrollmentTaskUpdate,
    bp: Annotated[BillingProvider, Depends(get_managed_billing_provider)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EnrollmentTaskRead:
    """Update a task's status, notes, or data (task must belong to this agency)."""
    result = await db.execute(select(EnrollmentTask).where(EnrollmentTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Confirm the task's service belongs to this agency
    await _get_service_in_agency(task.service_id, bp.id, db)

    if body.status == "complete" and task.task_key == "pcb_training_hours":
        hours = (body.task_data or {}).get("hours") or (task.task_data or {}).get("hours", 0)
        if int(hours) < 24:
            raise HTTPException(status_code=422, detail=f"Training hours must be ≥ 24 to complete this task (currently {hours}).")
    if body.status == "complete" and task.task_key == "pcb_hipaa_cert":
        hours = (body.task_data or {}).get("hours") or (task.task_data or {}).get("hours", 0)
        if int(hours) < 1:
            raise HTTPException(status_code=422, detail="HIPAA training hours must be ≥ 1 to complete this task.")

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


@router.get("/billing-admin/enrollment/services/{service_id}/documents/{doc_id}/url")
async def get_agency_enrollment_document_url(
    service_id: uuid.UUID,
    doc_id: uuid.UUID,
    bp: Annotated[BillingProvider, Depends(get_managed_billing_provider)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    await _get_service_in_agency(service_id, bp.id, db)
    doc_result = await db.execute(
        select(EnrollmentDocument).where(
            EnrollmentDocument.id == doc_id,
            EnrollmentDocument.service_id == service_id,
        )
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    from app.services.ocr_service import get_signed_url
    url = await get_signed_url(doc.file_path, expires_in=300)
    return {"url": url, "file_name": doc.file_name}


@router.delete(
    "/billing-admin/enrollment/services/{service_id}",
    status_code=204,
    response_class=Response,
)
async def delete_agency_enrollment_service(
    service_id: uuid.UUID,
    bp: Annotated[BillingProvider, Depends(require_billing_enrollment_tier)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
):
    """Delete an enrollment service that was started in error (not_started or in_progress only)."""
    service, _ = await _get_service_in_agency(service_id, bp.id, db)
    if service.status == "complete":
        raise HTTPException(status_code=409, detail="Cannot delete a completed enrollment service.")
    # Delete child tasks and documents first
    tasks_result = await db.execute(select(EnrollmentTask).where(EnrollmentTask.service_id == service_id))
    for task in tasks_result.scalars().all():
        await db.delete(task)
    docs_result = await db.execute(select(EnrollmentDocument).where(EnrollmentDocument.service_id == service_id))
    for doc in docs_result.scalars().all():
        try:
            from app.services.ocr_service import delete_file
            await delete_file(doc.file_path)
        except Exception:
            pass
        await db.delete(doc)
    await db.delete(service)
    await db.commit()
    await audit.log(
        db=db, action="DELETE_ENROLLMENT_SERVICE", resource_type="enrollment_service",
        resource_id=str(service_id), user_id=None, ip_address=get_client_ip(request),
        user_agent=get_user_agent(request), extra_context={"service_id": str(service_id)},
    )


@router.delete(
    "/billing-admin/enrollment/services/{service_id}/documents/{doc_id}",
    status_code=204,
    response_class=Response,
)
async def delete_agency_enrollment_document(
    service_id: uuid.UUID,
    doc_id: uuid.UUID,
    bp: Annotated[BillingProvider, Depends(get_managed_billing_provider)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _get_service_in_agency(service_id, bp.id, db)
    doc_result = await db.execute(
        select(EnrollmentDocument).where(
            EnrollmentDocument.id == doc_id,
            EnrollmentDocument.service_id == service_id,
        )
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    try:
        from app.services.ocr_service import delete_file
        await delete_file(doc.file_path)
    except Exception:
        pass
    await db.delete(doc)
    await db.commit()


# ── Stage-completion endpoints (enrollment tier required) ──────────────────────

@router.post(
    "/billing-admin/enrollment/services/{service_id}/complete-pcb",
    response_model=EnrollmentServiceRead,
)
async def billing_admin_complete_pcb(
    service_id: uuid.UUID,
    body: CompletePcbRequest,
    bp: Annotated[BillingProvider, Depends(require_billing_enrollment_tier)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> EnrollmentServiceRead:
    """Mark a PCB certification service complete and record the cert date."""
    service, provider = await _get_service_in_agency(service_id, bp.id, db)
    if service.stage != "pcb":
        raise HTTPException(status_code=422, detail="This endpoint is only for PCB Certification services.")
    if service.status == "complete":
        raise HTTPException(status_code=409, detail="Service is already marked complete.")

    service.status = "complete"
    service.pcb_cert_date = body.cert_date
    provider.pcb_last_certified_on = body.cert_date

    await db.commit()
    await db.refresh(service)

    await audit.log(
        action="BILLING_ADMIN_PCB_COMPLETE",
        user_id=current_user.id,
        resource_type="user",
        resource_id=provider.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        extra_context={"service_id": str(service_id), "cert_date": str(body.cert_date), "billing_provider_id": str(bp.id)},
    )
    return EnrollmentServiceRead.model_validate(service)


@router.post(
    "/billing-admin/enrollment/services/{service_id}/complete-nppes",
    response_model=EnrollmentServiceRead,
)
async def billing_admin_complete_nppes(
    service_id: uuid.UUID,
    body: CompleteNppesRequest,
    bp: Annotated[BillingProvider, Depends(require_billing_enrollment_tier)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> EnrollmentServiceRead:
    """Mark an NPPES/NPI Setup service complete and record the NPI."""
    service, provider = await _get_service_in_agency(service_id, bp.id, db)
    if service.stage != "nppes_setup":
        raise HTTPException(status_code=422, detail="This endpoint is only for NPPES/NPI Setup services.")
    if service.status == "complete":
        raise HTTPException(status_code=409, detail="Service is already marked complete.")

    npi = body.npi.strip()
    if not npi.isdigit() or len(npi) != 10:
        raise HTTPException(status_code=422, detail="NPI must be exactly 10 digits.")

    service.status = "complete"
    intake = dict(service.intake_data or {})
    intake["npi"] = npi
    service.intake_data = intake
    provider.npi = npi

    await db.commit()
    await db.refresh(service)

    await audit.log(
        action="BILLING_ADMIN_NPPES_COMPLETE",
        user_id=current_user.id,
        resource_type="user",
        resource_id=provider.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        extra_context={"service_id": str(service_id), "npi": npi, "billing_provider_id": str(bp.id)},
    )
    return EnrollmentServiceRead.model_validate(service)


@router.post(
    "/billing-admin/enrollment/services/{service_id}/complete-enrollment",
    response_model=EnrollmentServiceRead,
)
async def billing_admin_complete_enrollment(
    service_id: uuid.UUID,
    body: CompleteEnrollmentRequest,
    bp: Annotated[BillingProvider, Depends(require_billing_enrollment_tier)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> EnrollmentServiceRead:
    """Mark a PROMISe Enrollment service complete."""
    service, provider = await _get_service_in_agency(service_id, bp.id, db)
    if service.stage != "enrollment":
        raise HTTPException(status_code=422, detail="This endpoint is only for Stage 2 enrollment services.")
    if service.status == "complete":
        raise HTTPException(status_code=409, detail="Service is already marked complete.")

    service.status = "complete"
    intake = dict(service.intake_data or {})
    if body.promise_id:
        intake["promise_id"] = body.promise_id
    if body.caqh_id:
        intake["caqh_id"] = body.caqh_id
    service.intake_data = intake

    provider.promise_last_enrolled_on = body.promise_enrolled_on
    if body.liability_insurance_expires_on:
        provider.liability_insurance_expires_on = body.liability_insurance_expires_on

    await db.commit()
    await db.refresh(service)

    await audit.log(
        action="BILLING_ADMIN_ENROLLMENT_COMPLETE",
        user_id=current_user.id,
        resource_type="user",
        resource_id=provider.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        extra_context={"service_id": str(service_id), "promise_enrolled_on": str(body.promise_enrolled_on), "billing_provider_id": str(bp.id)},
    )
    return EnrollmentServiceRead.model_validate(service)


@router.post(
    "/billing-admin/enrollment/services/{service_id}/complete-mco-contracting",
    response_model=EnrollmentServiceRead,
)
async def billing_admin_complete_mco_contracting(
    service_id: uuid.UUID,
    body: CompleteMcoContractingRequest,
    bp: Annotated[BillingProvider, Depends(require_billing_enrollment_tier)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> EnrollmentServiceRead:
    """Mark an MCO Contracting service complete."""
    service, provider = await _get_service_in_agency(service_id, bp.id, db)
    if service.stage != "mco_contracting":
        raise HTTPException(status_code=422, detail="This endpoint is only for MCO Contracting services.")
    if service.status == "complete":
        raise HTTPException(status_code=409, detail="Service is already marked complete.")

    service.status = "complete"
    intake = dict(service.intake_data or {})
    intake["contracted_on"] = str(body.contracted_on)
    service.intake_data = intake

    await db.commit()
    await db.refresh(service)

    await audit.log(
        action="BILLING_ADMIN_MCO_CONTRACTING_COMPLETE",
        user_id=current_user.id,
        resource_type="user",
        resource_id=provider.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        extra_context={"service_id": str(service_id), "contracted_on": str(body.contracted_on), "billing_provider_id": str(bp.id)},
    )
    return EnrollmentServiceRead.model_validate(service)

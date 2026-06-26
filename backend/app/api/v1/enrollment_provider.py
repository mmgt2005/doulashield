"""Provider-facing enrollment endpoints — view status and upload documents."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.dependencies import CurrentUser, get_db, get_current_user
from app.models.enrollment import EnrollmentDocument, EnrollmentService, EnrollmentTask
from app.models.user import User
from app.schemas.enrollment import (
    EnrollmentDocumentRead,
    EnrollmentServiceDetail,
    EnrollmentServiceRead,
    EnrollmentTaskRead,
)

router = APIRouter(tags=["enrollment-provider"], prefix="/enrollment/me")

_MAX_BYTES = 20 * 1024 * 1024
_ALLOWED_TYPES = {"image/jpeg", "image/png", "application/pdf"}


@router.get("", response_model=list[EnrollmentServiceDetail])
async def get_my_enrollment_services(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[EnrollmentServiceDetail]:
    services_result = await db.execute(
        select(EnrollmentService)
        .where(EnrollmentService.provider_id == current_user.id)
        .order_by(EnrollmentService.created_at.desc())
    )
    services = services_result.scalars().all()

    out: list[EnrollmentServiceDetail] = []
    for service in services:
        tasks_result = await db.execute(
            select(EnrollmentTask)
            .where(EnrollmentTask.service_id == service.id)
            .order_by(EnrollmentTask.sort_order)
        )
        tasks = tasks_result.scalars().all()

        docs_result = await db.execute(
            select(EnrollmentDocument)
            .where(EnrollmentDocument.service_id == service.id)
            .order_by(EnrollmentDocument.created_at)
        )
        docs = docs_result.scalars().all()

        out.append(
            EnrollmentServiceDetail(
                service=EnrollmentServiceRead.model_validate(service),
                tasks=[EnrollmentTaskRead.model_validate(t) for t in tasks],
                documents=[EnrollmentDocumentRead.model_validate(d) for d in docs],
                provider_email=current_user.email,
                provider_name=current_user.full_name,
            )
        )
    return out


@router.post(
    "/{service_id}/tasks/{task_id}/documents",
    response_model=EnrollmentDocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_my_enrollment_document(
    service_id: uuid.UUID,
    task_id: uuid.UUID,
    file: UploadFile,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    document_type: Annotated[str, Form()] = "other",
) -> EnrollmentDocumentRead:
    from app.services.ocr_service import store_image

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

    service_result = await db.execute(
        select(EnrollmentService).where(EnrollmentService.id == service_id)
    )
    service = service_result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    if service.provider_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

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


@router.get("/agreement")
async def get_agreement_status(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    signed_at = user.surrogate_auth_signed_at
    return {
        "signed": signed_at is not None,
        "signed_at": signed_at.isoformat() if signed_at else None,
    }


@router.post("/sign-agreement")
async def sign_surrogate_agreement(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.surrogate_auth_signed_at is None:
        user.surrogate_auth_signed_at = datetime.now(timezone.utc)
        await db.commit()
    return {
        "signed": True,
        "signed_at": user.surrogate_auth_signed_at.isoformat(),
    }


@router.get("/{service_id}/documents/{doc_id}/url")
async def get_my_enrollment_document_url(
    service_id: uuid.UUID,
    doc_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    from app.services.ocr_service import get_signed_url

    service_result = await db.execute(
        select(EnrollmentService).where(EnrollmentService.id == service_id)
    )
    service = service_result.scalar_one_or_none()
    if not service or service.provider_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    doc_result = await db.execute(
        select(EnrollmentDocument).where(
            EnrollmentDocument.id == doc_id,
            EnrollmentDocument.service_id == service_id,
        )
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    url = await get_signed_url(doc.file_path)
    return {"url": url}

"""Provider-facing enrollment endpoints — view status and upload documents."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel
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


class _TaskDataPatch(BaseModel):
    task_data: dict

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

    user_result = await db.execute(select(User).where(User.id == current_user.id))
    user = user_result.scalar_one_or_none()

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
                provider_email=user.email if user else None,
                provider_name=user.full_name if user else None,
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


@router.patch("/{service_id}/tasks/{task_id}/data")
async def save_my_task_data(
    service_id: uuid.UUID,
    task_id: uuid.UUID,
    body: _TaskDataPatch,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service_result = await db.execute(
        select(EnrollmentService).where(EnrollmentService.id == service_id)
    )
    service = service_result.scalar_one_or_none()
    if not service or service.provider_id != current_user.id:
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

    task.task_data = body.task_data
    if task.status == "not_started":
        task.status = "in_progress"

    await db.commit()
    await db.refresh(task)
    return {"ok": True, "status": task.status}


@router.get("/{service_id}/pcb-prefill.pdf")
async def download_pcb_prefill(
    service_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    service_result = await db.execute(
        select(EnrollmentService).where(EnrollmentService.id == service_id)
    )
    service = service_result.scalar_one_or_none()
    if not service or service.provider_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if service.stage != "pcb":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Pre-fill PDF is only available for PCB enrollment services.",
        )

    tasks_result = await db.execute(
        select(EnrollmentTask)
        .where(EnrollmentTask.service_id == service_id)
        .order_by(EnrollmentTask.sort_order)
    )
    tasks = tasks_result.scalars().all()

    form_task = next((t for t in tasks if t.task_key == "pcb_application_form"), None)
    form_data: dict = dict(form_task.task_data or {}) if form_task else {}

    user_result = await db.execute(select(User).where(User.id == current_user.id))
    user = user_result.scalar_one_or_none()

    pdf_bytes = _build_pcb_prefill_pdf(
        form_data=form_data,
        tasks=list(tasks),
        service=service,
        provider_name=user.full_name if user else None,
        provider_email=user.email if user else "",
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=\"pcb-application-prefill.pdf\""},
    )


def _build_pcb_prefill_pdf(
    form_data: dict,
    tasks: list,
    service: object,
    provider_name: str | None,
    provider_email: str,
) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        HRFlowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.9 * inch,
        rightMargin=0.9 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
    )

    styles = getSampleStyleSheet()
    title_s = ParagraphStyle("DS_Title", parent=styles["Heading1"], fontSize=16, spaceAfter=4)
    sub_s = ParagraphStyle(
        "DS_Sub", parent=styles["Normal"], fontSize=9,
        textColor=colors.HexColor("#6B7280"), spaceAfter=14,
    )
    section_s = ParagraphStyle(
        "DS_Sec", parent=styles["Heading2"], fontSize=11, spaceBefore=14, spaceAfter=6,
    )
    lbl_s = ParagraphStyle(
        "DS_Lbl", parent=styles["Normal"], fontSize=7.5,
        textColor=colors.HexColor("#9CA3AF"), spaceAfter=2,
    )
    val_s = ParagraphStyle(
        "DS_Val", parent=styles["Normal"], fontSize=11, spaceAfter=10,
    )
    note_s = ParagraphStyle(
        "DS_Note", parent=styles["Normal"], fontSize=8,
        textColor=colors.HexColor("#6B7280"), spaceBefore=4, spaceAfter=4,
    )

    def field(label: str, value: str) -> None:
        story.append(Paragraph(label.upper(), lbl_s))
        story.append(Paragraph(value if value else "—", val_s))

    hr = HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E5E7EB"), spaceAfter=4)

    story: list = []

    story.append(Paragraph("PCB Application — Pre-fill Sheet", title_s))
    story.append(Paragraph(
        "Generated by DoulaShield. Transfer this information to the official PCB application. "
        "Download the blank official form at pacertboard.org/doula.",
        sub_s,
    ))
    story.append(hr)
    story.append(Spacer(1, 6))

    # ── Personal Information ───────────────────────────────────────────────────
    story.append(Paragraph("Section 1 — Personal Information (PCB Pages 6–7)", section_s))
    field("Full Name (exactly as it should appear on PCB certificate)", form_data.get("legal_name", ""))
    field("Date of Birth", form_data.get("dob", ""))
    field("Last 4 Digits of SSN", form_data.get("ssn_last4", ""))
    field("Phone Number", form_data.get("phone", ""))
    field("Email Address", form_data.get("email", ""))
    field("Street Address", form_data.get("address_street", ""))

    city = form_data.get("address_city", "")
    state = form_data.get("address_state", "")
    zip_code = form_data.get("address_zip", "")
    addr_table = Table(
        [
            [Paragraph("CITY", lbl_s), Paragraph("STATE", lbl_s), Paragraph("ZIP CODE", lbl_s)],
            [
                Paragraph(city or "—", val_s),
                Paragraph(state or "—", val_s),
                Paragraph(zip_code or "—", val_s),
            ],
        ],
        colWidths=[3.2 * inch, 1.4 * inch, 1.4 * inch],
    )
    addr_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(addr_table)
    story.append(Spacer(1, 8))

    # ── Demographics & Application Type ───────────────────────────────────────
    story.append(hr)
    story.append(Paragraph("Section 2 — Demographics & Application Type (PCB Pages 7–8)", section_s))
    field("Gender", form_data.get("gender", ""))
    field("Race / Ethnicity", form_data.get("race_ethnicity", ""))
    field("Primary Language", form_data.get("primary_language", ""))
    field("Doula Type", form_data.get("doula_type", ""))

    pathway_label = (
        "Education & Training (completed an approved program)"
        if getattr(service, "pcb_pathway", None) == "education_training"
        else "Experienced (5+ years without an approved training org)"
    )
    field("PCB Application Pathway", pathway_label)
    story.append(Paragraph(
        "Payment: $50 application fee — check payable to 'PCB' or per current payment instructions.",
        note_s,
    ))

    # ── Submission Checklist ───────────────────────────────────────────────────
    story.append(hr)
    story.append(Spacer(1, 4))
    story.append(Paragraph("Section 3 — Submission Checklist", section_s))
    story.append(Paragraph(
        "✓ = complete in DoulaShield  ◑ = in progress  ○ = not started",
        note_s,
    ))
    story.append(Spacer(1, 6))

    header_row = [
        Paragraph("", styles["Normal"]),
        Paragraph("<b>Item</b>", styles["Normal"]),
        Paragraph("<b>Status</b>", styles["Normal"]),
    ]
    rows = [header_row]
    for task in sorted(tasks, key=lambda t: t.sort_order):
        mark = "✓" if task.status == "complete" else ("◑" if task.status == "in_progress" else "○")
        status_text = task.status.replace("_", " ").title()
        rows.append([
            Paragraph(mark, styles["Normal"]),
            Paragraph(task.label, styles["Normal"]),
            Paragraph(status_text, styles["Normal"]),
        ])

    checklist = Table(rows, colWidths=[0.4 * inch, 4.6 * inch, 1.2 * inch])
    checklist.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(checklist)

    # ── Footer ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 14))
    story.append(hr)
    story.append(Paragraph(
        f"Generated for: {provider_email}  |  DoulaShield Enrollment Service: {service.id}",
        note_s,
    ))
    story.append(Paragraph(
        "Submit completed application to PCB: email info@pacertboard.org (PDF only), mail, or fax. "
        "Page 14 (Acknowledgements & Release) must be notarized before submission.",
        note_s,
    ))

    doc.build(story)
    return buf.getvalue()

"""Provider-facing enrollment endpoints — view status and upload documents."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import AuditLogger
from app.dependencies import CurrentUser, get_audit, get_client_ip, get_db, get_current_user, get_user_agent
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


class _BioBuildRequest(BaseModel):
    brain_dump: str


class _SensitiveProfilePatch(BaseModel):
    ssn: str | None = None
    dob: str | None = None
    tax_id: str | None = None

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


@router.post("/{service_id}/tasks/{task_id}/bio-build")
async def bio_build_work_history(
    service_id: uuid.UUID,
    task_id: uuid.UUID,
    body: _BioBuildRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Call Claude to convert a work history brain-dump into a structured table + gap log."""
    if not body.brain_dump.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="brain_dump is required")

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
    if task.task_key != "mco_work_history":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bio-build is only available for the 5-year work history task",
        )

    from app.services.work_history_service import process_work_history
    try:
        result = await process_work_history(body.brain_dump)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    existing = dict(task.task_data or {})
    existing["brain_dump"] = body.brain_dump
    existing["work_history_rows"] = result["rows"]
    existing["gap_log"] = result["gaps"]
    task.task_data = existing

    if task.status == "not_started":
        task.status = "in_progress"

    await db.commit()
    return {
        "ok": True,
        "rows": result["rows"],
        "gaps": result["gaps"],
    }


@router.get("/{service_id}/tasks/{task_id}/work-history.pdf")
async def download_work_history_pdf(
    service_id: uuid.UUID,
    task_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
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
    if not task or task.task_key != "mco_work_history":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work history task not found")

    td = dict(task.task_data or {})
    rows = td.get("work_history_rows") or []
    gaps = td.get("gap_log") or []

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No work history has been generated yet. Use the AI builder first.",
        )

    user_result = await db.execute(select(User).where(User.id == current_user.id))
    user = user_result.scalar_one_or_none()
    provider_name = user.full_name if user else ""

    pdf_bytes = _build_work_history_pdf(rows=rows, gaps=gaps, provider_name=provider_name)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=\"work-history.pdf\""},
    )


def _build_work_history_pdf(rows: list, gaps: list, provider_name: str) -> bytes:
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
    from datetime import date

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
    title_s = ParagraphStyle("WH_Title", parent=styles["Heading1"], fontSize=16, spaceAfter=4)
    sub_s = ParagraphStyle(
        "WH_Sub", parent=styles["Normal"], fontSize=9,
        textColor=colors.HexColor("#6B7280"), spaceAfter=14,
    )
    section_s = ParagraphStyle(
        "WH_Sec", parent=styles["Heading2"], fontSize=11, spaceBefore=14, spaceAfter=6,
    )
    cell_s = ParagraphStyle("WH_Cell", parent=styles["Normal"], fontSize=8, leading=10)
    note_s = ParagraphStyle(
        "WH_Note", parent=styles["Normal"], fontSize=8,
        textColor=colors.HexColor("#6B7280"), spaceBefore=4, spaceAfter=4,
    )

    hr = HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E5E7EB"), spaceAfter=4)
    story: list = []

    name_line = f" — {provider_name}" if provider_name else ""
    story.append(Paragraph(f"5-Year Work History{name_line}", title_s))
    story.append(Paragraph(
        f"Generated by DoulaShield on {date.today().strftime('%B %d, %Y')}. "
        "For PA Medicaid PROMISe™ and MCO credentialing.",
        sub_s,
    ))
    story.append(hr)

    # Work history table
    story.append(Paragraph("Employment History", section_s))

    col_headers = ["Start", "End", "Employer / Org", "Address", "Title / Role", "Duties"]
    col_widths = [0.65 * inch, 0.65 * inch, 1.3 * inch, 1.2 * inch, 1.1 * inch, 2.0 * inch]
    table_data = [[Paragraph(h, ParagraphStyle("WH_Hdr", parent=styles["Normal"], fontSize=7.5, fontName="Helvetica-Bold")) for h in col_headers]]

    for row in rows:
        table_data.append([
            Paragraph(str(row.get("start_date", "")), cell_s),
            Paragraph(str(row.get("end_date", "")), cell_s),
            Paragraph(str(row.get("employer_name", "")), cell_s),
            Paragraph(str(row.get("address", "")), cell_s),
            Paragraph(str(row.get("job_title", "")), cell_s),
            Paragraph(str(row.get("duties", "")), cell_s),
        ])

    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#374151")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(tbl)

    # Gap log
    if gaps:
        story.append(Spacer(1, 0.15 * inch))
        story.append(Paragraph("Gap Log — Periods Over 30 Days", section_s))
        story.append(Paragraph(
            "The following gaps were identified. Each gap requires an explanation when submitting to MCOs.",
            note_s,
        ))
        gap_data = [[
            Paragraph("From", ParagraphStyle("WH_GHdr", parent=styles["Normal"], fontSize=7.5, fontName="Helvetica-Bold")),
            Paragraph("To", ParagraphStyle("WH_GHdr", parent=styles["Normal"], fontSize=7.5, fontName="Helvetica-Bold")),
            Paragraph("Days", ParagraphStyle("WH_GHdr", parent=styles["Normal"], fontSize=7.5, fontName="Helvetica-Bold")),
            Paragraph("Explanation", ParagraphStyle("WH_GHdr", parent=styles["Normal"], fontSize=7.5, fontName="Helvetica-Bold")),
        ]]
        for g in gaps:
            gap_data.append([
                Paragraph(str(g.get("start_date", "")), cell_s),
                Paragraph(str(g.get("end_date", "")), cell_s),
                Paragraph(str(g.get("duration_days", "")), cell_s),
                Paragraph(str(g.get("explanation", "")), cell_s),
            ])
        gap_tbl = Table(gap_data, colWidths=[0.75 * inch, 0.75 * inch, 0.5 * inch, 4.9 * inch], repeatRows=1)
        gap_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FEF3C7")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#92400E")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FFFBEB")]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#FDE68A")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(gap_tbl)

    story.append(Spacer(1, 0.2 * inch))
    story.append(hr)
    story.append(Paragraph(
        "This document was generated from DoulaShield. Verify all information before submitting to MCOs or PROMISe™.",
        note_s,
    ))

    doc.build(story)
    return buf.getvalue()


class _ResumeRequest(BaseModel):
    name: str = ""
    certs: str = ""
    history: str = ""
    philosophy: str = ""


@router.post("/{service_id}/tasks/{task_id}/resume-build")
async def resume_build(
    service_id: uuid.UUID,
    task_id: uuid.UUID,
    body: _ResumeRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Call Claude to generate a structured MCO-compliant CV from provider inputs."""
    if not any([body.name.strip(), body.certs.strip(), body.history.strip(), body.philosophy.strip()]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one field is required")

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
    if task.task_key != "mco_resume_cv":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume build is only available for the Resume / CV task",
        )

    from app.services.resume_service import process_resume
    try:
        result = await process_resume(body.name, body.certs, body.history, body.philosophy)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    existing = dict(task.task_data or {})
    existing["resume_name"] = body.name
    existing["resume_certs"] = body.certs
    existing["resume_history"] = body.history
    existing["resume_philosophy"] = body.philosophy
    existing["resume_sections"] = result
    task.task_data = existing

    if task.status == "not_started":
        task.status = "in_progress"

    await db.commit()
    return {"ok": True, "sections": result}


@router.get("/{service_id}/tasks/{task_id}/resume.pdf")
async def download_resume_pdf(
    service_id: uuid.UUID,
    task_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
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
    if not task or task.task_key != "mco_resume_cv":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume task not found")

    td = dict(task.task_data or {})
    sections = td.get("resume_sections")
    if not sections:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No resume has been generated yet. Use the AI builder first.",
        )

    pdf_bytes = _build_resume_pdf(sections)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=\"resume-cv.pdf\""},
    )


def _build_resume_pdf(sections: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import HRFlowable, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from datetime import date

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=0.85 * inch, rightMargin=0.85 * inch,
        topMargin=0.85 * inch, bottomMargin=0.85 * inch,
    )

    styles = getSampleStyleSheet()
    name_s = ParagraphStyle("R_Name", parent=styles["Heading1"], fontSize=18, spaceAfter=2, leading=22)
    cred_s = ParagraphStyle("R_Cred", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#4B5563"), spaceAfter=12)
    section_s = ParagraphStyle("R_Sec", parent=styles["Heading2"], fontSize=11, spaceBefore=12, spaceAfter=4, textColor=colors.HexColor("#1D4ED8"), borderPad=0)
    body_s = ParagraphStyle("R_Body", parent=styles["Normal"], fontSize=9, leading=13, spaceAfter=6)
    cell_s = ParagraphStyle("R_Cell", parent=styles["Normal"], fontSize=8, leading=10)
    bullet_s = ParagraphStyle("R_Bull", parent=styles["Normal"], fontSize=9, leading=12)
    note_s = ParagraphStyle("R_Note", parent=styles["Normal"], fontSize=7.5, textColor=colors.HexColor("#9CA3AF"), spaceBefore=8)

    hr = HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#DBEAFE"), spaceAfter=4)

    story: list = []

    # Header
    creds = sections.get("credentials_line", "")
    parts = creds.split("|", 1)
    name_part = parts[0].strip()
    rest_part = parts[1].strip() if len(parts) > 1 else ""

    story.append(Paragraph(name_part, name_s))
    if rest_part:
        story.append(Paragraph(rest_part, cred_s))
    story.append(Paragraph(
        f"CV generated by DoulaShield on {date.today().strftime('%B %d, %Y')} · PA Medicaid PROMISe™ &amp; MCO Credentialing",
        note_s,
    ))
    story.append(Spacer(1, 0.1 * inch))
    story.append(hr)

    # Professional summary
    summary = sections.get("professional_summary", "")
    if summary:
        story.append(Paragraph("Professional Summary", section_s))
        story.append(hr)
        story.append(Paragraph(summary, body_s))

    # Certifications
    certs = sections.get("certifications", [])
    if certs:
        story.append(Paragraph("Certifications &amp; Credentials", section_s))
        story.append(hr)
        cert_rows = [["Certification", "Issuing Organization", "Date", "Expires"]]
        for c in certs:
            cert_rows.append([
                Paragraph(str(c.get("name", "")), cell_s),
                Paragraph(str(c.get("issuer", "")), cell_s),
                Paragraph(str(c.get("date", "")), cell_s),
                Paragraph(str(c.get("expires") or "—"), cell_s),
            ])
        cert_tbl = Table(cert_rows, colWidths=[2.2 * inch, 2.0 * inch, 1.0 * inch, 1.0 * inch], repeatRows=1)
        cert_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFF6FF")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1E40AF")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(cert_tbl)

    # Experience
    experience = sections.get("experience", [])
    if experience:
        story.append(Paragraph("Professional Experience", section_s))
        story.append(hr)
        exp_rows = [["Start", "End", "Employer", "Location", "Title", "Duties"]]
        for e in experience:
            exp_rows.append([
                Paragraph(str(e.get("start_date", "")), cell_s),
                Paragraph(str(e.get("end_date", "")), cell_s),
                Paragraph(str(e.get("employer", "")), cell_s),
                Paragraph(str(e.get("location", "")), cell_s),
                Paragraph(str(e.get("title", "")), cell_s),
                Paragraph(str(e.get("duties", "")), cell_s),
            ])
        exp_tbl = Table(exp_rows, colWidths=[0.6 * inch, 0.6 * inch, 1.3 * inch, 1.0 * inch, 1.1 * inch, 2.2 * inch], repeatRows=1)
        exp_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFF6FF")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1E40AF")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7.5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(exp_tbl)

    # Education
    education = sections.get("education", [])
    if education:
        story.append(Paragraph("Education &amp; Training", section_s))
        story.append(hr)
        for ed in education:
            hours = f" ({ed.get('hours')} hrs)" if ed.get("hours") else ""
            line = f"<b>{ed.get('program', '')}</b> — {ed.get('institution', '')} · {ed.get('year', '')}{hours}"
            story.append(Paragraph(line, body_s))

    # Skills
    skills = sections.get("skills", [])
    if skills:
        story.append(Paragraph("Core Competencies", section_s))
        story.append(hr)
        items = [ListItem(Paragraph(s, bullet_s), leftIndent=12, bulletColor=colors.HexColor("#3B82F6")) for s in skills]
        story.append(ListFlowable(items, bulletType="bullet", bulletFontSize=6, leftIndent=0, spaceBefore=0))

    # Philosophy
    philosophy = sections.get("philosophy", "")
    if philosophy:
        story.append(Paragraph("Philosophy of Care", section_s))
        story.append(hr)
        story.append(Paragraph(philosophy, body_s))

    story.append(Spacer(1, 0.2 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E5E7EB"), spaceAfter=4))
    story.append(Paragraph(
        "Generated by DoulaShield. Review all information for accuracy before submitting to MCOs or PROMISe™.",
        note_s,
    ))

    doc.build(story)
    return buf.getvalue()


@router.get("/sensitive-profile")
async def get_sensitive_profile(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    client_ip: Annotated[str | None, Depends(get_client_ip)],
    user_agent: Annotated[str, Depends(get_user_agent)],
) -> dict:
    from app.core.encryption import decrypt_field

    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    has_ssn = bool(user.provider_ssn_encrypted)
    ssn_last4: str | None = None
    if has_ssn:
        try:
            decrypted_ssn = decrypt_field(user.provider_ssn_encrypted)
            ssn_last4 = decrypted_ssn[-4:] if len(decrypted_ssn) >= 4 else decrypted_ssn
        except Exception:
            has_ssn = False

    has_dob = bool(user.provider_dob_encrypted)
    dob: str | None = None
    if has_dob:
        try:
            dob = decrypt_field(user.provider_dob_encrypted)
        except Exception:
            has_dob = False

    has_tax_id = bool(user.enrollment_tax_id_encrypted)

    await audit.log(
        action="READ_ENROLLMENT_SENSITIVE",
        ip_address=client_ip,
        user_agent=user_agent,
        user_id=current_user.id,
        resource_type="user",
        resource_id=current_user.id,
    )

    return {
        "has_ssn": has_ssn,
        "ssn_last4": ssn_last4,
        "has_dob": has_dob,
        "dob": dob,
        "has_tax_id": has_tax_id,
    }


@router.patch("/sensitive-profile")
async def update_sensitive_profile(
    body: _SensitiveProfilePatch,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    client_ip: Annotated[str | None, Depends(get_client_ip)],
    user_agent: Annotated[str, Depends(get_user_agent)],
) -> dict:
    from app.core.encryption import encrypt_field

    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    updated_fields: list[str] = []

    if body.ssn is not None:
        ssn_clean = body.ssn.replace("-", "").replace(" ", "")
        if not ssn_clean.isdigit() or len(ssn_clean) not in (4, 9):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="SSN must be 4 or 9 digits (hyphens are stripped automatically).",
            )
        user.provider_ssn_encrypted = encrypt_field(ssn_clean)
        updated_fields.append("ssn")

    if body.dob is not None:
        if body.dob and len(body.dob) > 20:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid date of birth.",
            )
        user.provider_dob_encrypted = encrypt_field(body.dob)
        updated_fields.append("dob")

    if body.tax_id is not None:
        user.enrollment_tax_id_encrypted = encrypt_field(body.tax_id) if body.tax_id else None
        updated_fields.append("tax_id")

    if updated_fields:
        await db.commit()

    await audit.log(
        action="WRITE_ENROLLMENT_SENSITIVE",
        ip_address=client_ip,
        user_agent=user_agent,
        user_id=current_user.id,
        resource_type="user",
        resource_id=current_user.id,
        extra_context={"fields": updated_fields},
    )

    return {"ok": True, "updated": updated_fields}


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

    from app.core.encryption import decrypt_field

    ssn_last4: str = ""
    if user and user.provider_ssn_encrypted:
        try:
            dec = decrypt_field(user.provider_ssn_encrypted)
            ssn_last4 = dec[-4:] if len(dec) >= 4 else dec
        except Exception:
            pass

    dob: str = ""
    if user and user.provider_dob_encrypted:
        try:
            dob = decrypt_field(user.provider_dob_encrypted)
        except Exception:
            pass

    pdf_bytes = _build_pcb_prefill_pdf(
        form_data=form_data,
        tasks=list(tasks),
        service=service,
        provider_name=user.full_name if user else None,
        provider_email=user.email if user else "",
        ssn_last4=ssn_last4,
        dob=dob,
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
    ssn_last4: str = "",
    dob: str = "",
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
    field("Date of Birth", dob)
    field("Last 4 Digits of SSN", ssn_last4)
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

from __future__ import annotations

import logging
import uuid
from typing import Annotated, Literal

from pydantic import BaseModel

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, status

from app.core.audit import AuditLogger
from app.dependencies import CurrentUser, get_audit, get_client_ip, get_current_user, get_user_agent
from app.services import ocr_service

router = APIRouter(prefix="/ocr", tags=["ocr"])

_MAX_BYTES = 20 * 1024 * 1024  # 20 MB (PDFs can be larger than photos)
_ALLOWED_TYPES = {"image/jpeg", "image/png", "application/pdf"}
# page_types that accept PDF in addition to images (EOBs are commonly digital PDFs)
_PDF_ALLOWED_PAGE_TYPES = {"remittance_eob"}


async def _read_upload(file: UploadFile, allow_pdf: bool = False) -> tuple[bytes, str]:
    content_type = file.content_type or ""
    allowed = _ALLOWED_TYPES if allow_pdf else {"image/jpeg", "image/png"}
    if content_type not in allowed:
        detail = (
            "Only JPEG, PNG, or PDF files are accepted."
            if allow_pdf
            else "Only JPEG and PNG images are accepted."
        )
        raise HTTPException(status_code=400, detail=detail)
    data = await file.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="File must be under 20 MB.")
    return data, content_type


@router.post("/medicaid-card")
async def scan_medicaid_card(
    request: Request,
    file: UploadFile,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    patient_id: Annotated[str | None, Form()] = None,
) -> dict:
    """Scan a Medicaid card image and extract name, medicaid_id, and MCO."""
    image_bytes, content_type = await _read_upload(file)

    pid: uuid.UUID | None = None
    if patient_id:
        try:
            pid = uuid.UUID(patient_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid patient_id.")

    image_path: str | None = None
    try:
        image_path = await ocr_service.store_image(
            image_bytes, content_type, pid, current_user.id, "medicaid-card"
        )
    except Exception as _store_err:
        logger.warning("Storage upload failed (non-blocking): %s", _store_err)

    try:
        extracted = await ocr_service.extract_image(image_bytes, content_type, "medicaid_card")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not read image — please try a clearer photo.",
        )

    await audit.log(
        action="SCAN_MEDICAID_CARD",
        resource_type="patient" if pid else None,
        resource_id=pid,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        user_id=current_user.id,
    )

    return {**extracted, "image_path": image_path}


@router.post("/handbook")
async def scan_handbook(
    request: Request,
    file: UploadFile,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    page_type: Annotated[Literal["soap_note", "prenatal", "birth", "ma_589", "access_card", "remittance_eob"], Form()],
    patient_id: Annotated[str | None, Form()] = None,
) -> dict:
    """Scan a handwritten handbook page and extract structured visit data."""
    image_bytes, content_type = await _read_upload(file, allow_pdf=page_type in _PDF_ALLOWED_PAGE_TYPES)

    pid: uuid.UUID | None = None
    if patient_id:
        try:
            pid = uuid.UUID(patient_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid patient_id.")

    image_path: str | None = None
    try:
        image_path = await ocr_service.store_image(
            image_bytes, content_type, pid, current_user.id, page_type
        )
    except Exception as _store_err:
        logger.warning("Storage upload failed (non-blocking): %s", _store_err)

    try:
        extracted = await ocr_service.extract_image(image_bytes, content_type, page_type)
    except ValueError as exc:
        msg = str(exc)
        if "scanned image" in msg or "no extractable text" in msg.lower():
            detail = "This PDF appears to be a scanned image — please photograph the paper remittance instead, or use a digital EOB PDF."
        elif "corrupted" in msg or "password" in msg:
            detail = "Could not open the PDF — it may be password-protected or corrupted."
        else:
            detail = "Could not read the file — please try a clearer photo or a digital EOB PDF."
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

    await audit.log(
        action="SCAN_HANDBOOK_PAGE",
        resource_type="patient" if pid else None,
        resource_id=pid,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        user_id=current_user.id,
        extra_context={"page_type": page_type},
    )

    return {**extracted, "image_path": image_path}


class _SoapTranslateRequest(BaseModel):
    subjective: str | None = None
    objective: str | None = None
    assessment: str | None = None
    plan: str | None = None
    patient_id: uuid.UUID | None = None


@router.post("/soap-translate")
async def translate_soap_note(
    request: Request,
    body: _SoapTranslateRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> dict:
    """Translate plain-language SOAP fields into professional clinical documentation."""
    try:
        result = await ocr_service.translate_soap({
            "subjective": body.subjective,
            "objective": body.objective,
            "assessment": body.assessment,
            "plan": body.plan,
        })
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="SOAP translation failed — please try again.",
        )

    await audit.log(
        action="TRANSLATE_SOAP_NOTE",
        resource_type="patient" if body.patient_id else None,
        resource_id=body.patient_id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        user_id=current_user.id,
        extra_context={"patient_id": str(body.patient_id)} if body.patient_id else None,
    )

    return result


@router.get("/image")
async def get_image_url(
    request: Request,
    path: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> dict:
    """Return a 60-second signed URL for a stored document image."""
    try:
        url = await ocr_service.get_signed_url(path)
    except Exception:
        raise HTTPException(status_code=404, detail="Image not found.")

    await audit.log(
        action="DOWNLOAD_DOCUMENT_IMAGE",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        user_id=current_user.id,
        extra_context={"path": path},
    )

    return {"url": url}

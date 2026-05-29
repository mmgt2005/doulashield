from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.core.audit import AuditLogger
from app.dependencies import CurrentUser, get_audit, get_client_ip, get_current_user, get_db, get_user_agent
from app.services import signature_service
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(tags=["signatures"])


class _InPersonSignRequest(BaseModel):
    signature_data_url: str
    patient_name: str


class _TelehealthSignRequest(BaseModel):
    patient_email: str
    patient_name: str
    visit_date: str = ""


class _WebhookPayload(BaseModel):
    event: str = ""
    metadata: dict = {}


@router.post("/patients/{patient_id}/visits/{visit_type}/sign-in-person")
async def sign_in_person(
    request: Request,
    patient_id: uuid.UUID,
    visit_type: str,
    body: _InPersonSignRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Save a canvas signature for an in-person MA 91 encounter form."""
    from sqlalchemy.future import select
    from app.models.visit import Visit

    result = await db.execute(
        select(Visit).where(
            Visit.patient_id == patient_id,
            Visit.visit_type == visit_type,
            Visit.provider_id == current_user.id,
        )
    )
    visit = result.scalar_one_or_none()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found.")

    try:
        return await signature_service.save_in_person_signature(
            image_data_url=body.signature_data_url,
            visit_id=visit.id,
            patient_id=patient_id,
            patient_name=body.patient_name,
            user_id=current_user.id,
            db=db,
            audit=audit,
            ip=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error("In-person signature save failed: %s", exc)
        raise HTTPException(status_code=500, detail="Signature save failed — please try again.")


@router.post("/patients/{patient_id}/visits/{visit_type}/request-telehealth-signature")
async def request_telehealth_signature(
    request: Request,
    patient_id: uuid.UUID,
    visit_type: str,
    body: _TelehealthSignRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Send a ZipZign e-signature request for a telehealth MA 91 encounter form."""
    from sqlalchemy.future import select
    from app.models.visit import Visit

    result = await db.execute(
        select(Visit).where(
            Visit.patient_id == patient_id,
            Visit.visit_type == visit_type,
            Visit.provider_id == current_user.id,
        )
    )
    visit = result.scalar_one_or_none()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found.")

    visit_date = body.visit_date or (visit.visit_date.isoformat() if visit.visit_date else "N/A")

    try:
        return await signature_service.request_telehealth_signature(
            provider_user_id=current_user.id,
            patient_name=body.patient_name,
            patient_email=body.patient_email,
            visit_date=visit_date,
            visit_id=visit.id,
            patient_id=patient_id,
            db=db,
            audit=audit,
            ip=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error("Telehealth signature request failed: %s", exc)
        raise HTTPException(status_code=500, detail="Signature request failed — please try again.")


@router.post("/signatures/webhook", status_code=200)
async def zipzign_webhook(
    request: Request,
    body: _WebhookPayload,
    audit: Annotated[AuditLogger, Depends(get_audit)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Receive ZipZign webhook events for MA 91 signature completion."""
    from app.core.config import settings

    if settings.ZIPZIGN_WEBHOOK_SECRET:
        incoming = request.headers.get("X-ZipZign-Signature", "")
        if incoming != settings.ZIPZIGN_WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="Invalid webhook signature.")

    try:
        await signature_service.handle_zipzign_webhook(
            payload=body.model_dump(),
            db=db,
            audit=audit,
        )
    except Exception as exc:
        logger.error("Webhook processing error: %s", exc)

    return {"received": True}

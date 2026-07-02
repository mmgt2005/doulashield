import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.lead import Lead
from app.schemas.lead import ContactLeadCreate, QuizLeadCreate, WebinarLeadCreate

log = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/public/leads", tags=["public"])


async def _find_existing(db: AsyncSession, email: str, source: str) -> Lead | None:
    result = await db.execute(
        select(Lead).where(Lead.email == email, Lead.source == source)
    )
    return result.scalar_one_or_none()


async def _notify_admin(lead: Lead) -> None:
    try:
        from app.services.email_service import send_new_lead_notification
        await send_new_lead_notification(lead)
    except Exception:
        log.warning("Failed to send admin lead notification", exc_info=True)


async def _notify_prospect_quiz(lead: Lead, answers: dict | None) -> None:
    if not answers:
        return
    try:
        from app.services.email_service import send_quiz_results_email
        await send_quiz_results_email(lead, answers)
    except Exception:
        log.warning("Failed to send quiz results to prospect", exc_info=True)


async def _notify_prospect_webinar(lead: Lead, webinar_topic: str | None = None) -> None:
    try:
        from app.core.config import settings
        from app.services.email_service import send_webinar_confirmation
        topic = (webinar_topic or "").lower()
        if "agency" in topic:
            video_url = settings.WEBINAR_VIDEO_URL_AGENCY or settings.WEBINAR_VIDEO_URL
        else:
            video_url = settings.WEBINAR_VIDEO_URL
        await send_webinar_confirmation(lead, video_url=video_url)
    except Exception:
        log.warning("Failed to send webinar confirmation to prospect", exc_info=True)


@router.post("/webinar", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register_webinar_lead(
    request: Request,
    body: WebinarLeadCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    email = str(body.email).lower()
    existing = await _find_existing(db, email, "webinar")

    if existing:
        if existing.converted_user_id:
            return {"status": "ok", "id": str(existing.id)}
        existing.lead_data = {"webinar_topic": body.webinar_topic} if body.webinar_topic else existing.lead_data
        existing.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(existing)
        await _notify_prospect_webinar(existing, body.webinar_topic)
        log.info("Duplicate webinar lead updated: <%s>", email)
        return {"status": "ok", "id": str(existing.id)}

    lead = Lead(
        source="webinar",
        status="new",
        first_name=body.first_name,
        last_name=body.last_name,
        email=email,
        phone=body.phone,
        organization_name=body.organization_name,
        provider_type="unknown",
        lead_data={"webinar_topic": body.webinar_topic} if body.webinar_topic else None,
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    await _notify_admin(lead)
    await _notify_prospect_webinar(lead, body.webinar_topic)
    log.info("New webinar lead: %s %s <%s>", body.first_name, body.last_name, email)
    return {"status": "ok", "id": str(lead.id)}


@router.post("/quiz", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register_quiz_lead(
    request: Request,
    body: QuizLeadCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    email = str(body.email).lower()
    existing = await _find_existing(db, email, "quiz")

    if existing:
        if existing.converted_user_id:
            return {"status": "ok", "id": str(existing.id)}
        existing.lead_data = {"answers": body.answers} if body.answers else existing.lead_data
        existing.provider_type = body.provider_type or existing.provider_type
        existing.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(existing)
        await _notify_prospect_quiz(existing, body.answers)
        log.info("Duplicate quiz lead updated: <%s>", email)
        return {"status": "ok", "id": str(existing.id)}

    lead = Lead(
        source="quiz",
        status="new",
        first_name=body.first_name,
        last_name=body.last_name,
        email=email,
        phone=body.phone,
        organization_name=body.organization_name,
        provider_type=body.provider_type,
        lead_data={"answers": body.answers} if body.answers else None,
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    await _notify_admin(lead)
    await _notify_prospect_quiz(lead, body.answers)
    log.info("New quiz lead: %s %s <%s>", body.first_name, body.last_name, email)
    return {"status": "ok", "id": str(lead.id)}


@router.post("/contact", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register_contact_lead(
    request: Request,
    body: ContactLeadCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    email = str(body.email).lower()
    existing = await _find_existing(db, email, "contact_form")

    if existing:
        if existing.converted_user_id:
            return {"status": "ok", "id": str(existing.id)}
        existing.lead_data = {"message": body.message} if body.message else existing.lead_data
        existing.updated_at = datetime.now(timezone.utc)
        await db.commit()
        log.info("Duplicate contact lead updated: <%s>", email)
        return {"status": "ok", "id": str(existing.id)}

    lead = Lead(
        source="contact_form",
        status="new",
        first_name=body.first_name,
        last_name=body.last_name,
        email=email,
        phone=body.phone,
        organization_name=body.organization_name,
        provider_type=body.provider_type,
        lead_data={"message": body.message} if body.message else None,
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    await _notify_admin(lead)
    log.info("New contact lead: %s %s <%s>", body.first_name, body.last_name, email)
    return {"status": "ok", "id": str(lead.id)}

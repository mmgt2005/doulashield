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


async def _find_existing(db: AsyncSession, email: str) -> Lead | None:
    result = await db.execute(
        select(Lead).where(Lead.email == email).order_by(Lead.created_at.desc())
    )
    return result.scalars().first()


async def _notify_admin(lead: Lead, db: AsyncSession | None = None) -> None:
    try:
        from app.services.email_service import send_new_lead_notification
        await send_new_lead_notification(lead)
    except Exception:
        log.warning("Failed to send admin lead notification", exc_info=True)
    if db is not None:
        try:
            from app.services.push_service import notify_admins_new_lead
            name = f"{lead.first_name or ''} {lead.last_name or ''}".strip() or lead.email or "Unknown"
            await notify_admins_new_lead(db, name, lead.email or "")
        except Exception:
            log.warning("Failed to push new lead to admins", exc_info=True)


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
    existing = await _find_existing(db, email)

    if existing:
        updated_data = dict(existing.lead_data or {})
        if body.webinar_topic:
            updated_data["webinar_topic"] = body.webinar_topic
        existing.lead_data = updated_data or existing.lead_data
        existing.first_name = body.first_name or existing.first_name
        existing.last_name = body.last_name or existing.last_name
        if body.phone:
            existing.phone = body.phone
        if body.organization_name:
            existing.organization_name = body.organization_name
        existing.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(existing)
        if not existing.converted_user_id:
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
    await _notify_admin(lead, db)
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
    existing = await _find_existing(db, email)

    if existing:
        updated_data = dict(existing.lead_data or {})
        if body.answers:
            updated_data["answers"] = body.answers
        if body.webinar_reached_at:
            updated_data["webinar_reached_at"] = body.webinar_reached_at
        if body.webinar_cta_clicked_at:
            updated_data["webinar_cta_clicked_at"] = body.webinar_cta_clicked_at
        existing.lead_data = updated_data or existing.lead_data
        existing.first_name = body.first_name or existing.first_name
        existing.last_name = body.last_name or existing.last_name
        if body.phone:
            existing.phone = body.phone
        if body.organization_name:
            existing.organization_name = body.organization_name
        if body.provider_type and body.provider_type != "unknown":
            existing.provider_type = body.provider_type
        existing.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(existing)
        if not existing.converted_user_id:
            await _notify_prospect_quiz(existing, body.answers)
        log.info("Duplicate quiz lead updated: <%s>", email)
        return {"status": "ok", "id": str(existing.id)}

    quiz_data: dict = {}
    if body.answers:
        quiz_data["answers"] = body.answers
    if body.webinar_reached_at:
        quiz_data["webinar_reached_at"] = body.webinar_reached_at
    if body.webinar_cta_clicked_at:
        quiz_data["webinar_cta_clicked_at"] = body.webinar_cta_clicked_at
    lead = Lead(
        source="quiz",
        status="new",
        first_name=body.first_name,
        last_name=body.last_name,
        email=email,
        phone=body.phone,
        organization_name=body.organization_name,
        provider_type=body.provider_type,
        lead_data=quiz_data or None,
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    await _notify_admin(lead, db)
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
    existing = await _find_existing(db, email)

    if existing:
        updated_data = dict(existing.lead_data or {})
        if body.message:
            updated_data["message"] = body.message
        if body.webinar_reached_at:
            updated_data["webinar_reached_at"] = body.webinar_reached_at
        if body.webinar_cta_clicked_at:
            updated_data["webinar_cta_clicked_at"] = body.webinar_cta_clicked_at
        existing.lead_data = updated_data or existing.lead_data
        existing.first_name = body.first_name or existing.first_name
        existing.last_name = body.last_name or existing.last_name
        if body.phone:
            existing.phone = body.phone
        if body.organization_name:
            existing.organization_name = body.organization_name
        if body.provider_type and body.provider_type != "unknown":
            existing.provider_type = body.provider_type
        existing.updated_at = datetime.now(timezone.utc)
        await db.commit()
        log.info("Duplicate contact lead updated: <%s>", email)
        return {"status": "ok", "id": str(existing.id)}

    contact_data: dict = {}
    if body.message:
        contact_data["message"] = body.message
    if body.webinar_reached_at:
        contact_data["webinar_reached_at"] = body.webinar_reached_at
    if body.webinar_cta_clicked_at:
        contact_data["webinar_cta_clicked_at"] = body.webinar_cta_clicked_at
    lead = Lead(
        source="contact_form",
        status="new",
        first_name=body.first_name,
        last_name=body.last_name,
        email=email,
        phone=body.phone,
        organization_name=body.organization_name,
        provider_type=body.provider_type,
        lead_data=contact_data or None,
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    await _notify_admin(lead, db)
    log.info("New contact lead: %s %s <%s>", body.first_name, body.last_name, email)
    return {"status": "ok", "id": str(lead.id)}

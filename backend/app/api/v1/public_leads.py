import logging

from fastapi import APIRouter, Depends, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.lead import Lead
from app.schemas.lead import ContactLeadCreate, QuizLeadCreate, WebinarLeadCreate

log = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/public/leads", tags=["public"])


async def _notify_admin(lead: Lead) -> None:
    try:
        from app.services.email_service import send_new_lead_notification
        await send_new_lead_notification(lead)
    except Exception:
        log.warning("Failed to send admin lead notification", exc_info=True)


@router.post("/webinar", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register_webinar_lead(
    request: Request,
    body: WebinarLeadCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    lead = Lead(
        source="webinar",
        status="new",
        first_name=body.first_name,
        last_name=body.last_name,
        email=str(body.email),
        phone=body.phone,
        organization_name=body.organization_name,
        provider_type="unknown",
        lead_data={"webinar_topic": body.webinar_topic} if body.webinar_topic else None,
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    await _notify_admin(lead)
    log.info("New webinar lead: %s %s <%s>", body.first_name, body.last_name, body.email)
    return {"status": "ok", "id": str(lead.id)}


@router.post("/quiz", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register_quiz_lead(
    request: Request,
    body: QuizLeadCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    lead = Lead(
        source="quiz",
        status="new",
        first_name=body.first_name,
        last_name=body.last_name,
        email=str(body.email),
        phone=body.phone,
        organization_name=body.organization_name,
        provider_type=body.provider_type,
        lead_data={"answers": body.answers} if body.answers else None,
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    await _notify_admin(lead)
    log.info("New quiz lead: %s %s <%s>", body.first_name, body.last_name, body.email)
    return {"status": "ok", "id": str(lead.id)}


@router.post("/contact", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register_contact_lead(
    request: Request,
    body: ContactLeadCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    lead = Lead(
        source="contact_form",
        status="new",
        first_name=body.first_name,
        last_name=body.last_name,
        email=str(body.email),
        phone=body.phone,
        organization_name=body.organization_name,
        provider_type=body.provider_type,
        lead_data={"message": body.message} if body.message else None,
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    await _notify_admin(lead)
    log.info("New contact lead: %s %s <%s>", body.first_name, body.last_name, body.email)
    return {"status": "ok", "id": str(lead.id)}

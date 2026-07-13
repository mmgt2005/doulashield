import logging
import secrets
import string
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import AuditLogger
from app.core.config import settings
from app.dependencies import CurrentUser, get_audit, get_client_ip, get_db, get_user_agent, require_admin
from app.models.lead import Lead
from app.models.user import User
from app.schemas.admin import UserCreate
from app.schemas.lead import LeadCreate, LeadRead, LeadUpdate
from app.services.admin_service import AdminService

log = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/leads", tags=["admin"])

_SPECIAL = "!@#$%^&*"
_POOL = string.ascii_letters + string.digits + _SPECIAL


def _gen_password() -> str:
    while True:
        pwd = "".join(secrets.choice(_POOL) for _ in range(14))
        if (
            any(c.isupper() for c in pwd)
            and any(c.islower() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in _SPECIAL for c in pwd)
        ):
            return pwd


@router.get("", response_model=list[LeadRead])
async def list_leads(
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    source: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    provider_type: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    search: str | None = Query(None),
) -> list[LeadRead]:
    q = select(Lead).order_by(Lead.created_at.desc())
    if source:
        q = q.where(Lead.source == source)
    if status_filter:
        q = q.where(Lead.status == status_filter)
    if provider_type:
        q = q.where(Lead.provider_type == provider_type)
    if date_from:
        q = q.where(Lead.created_at >= date_from)
    if date_to:
        q = q.where(Lead.created_at <= date_to)
    if search:
        term = f"%{search}%"
        q = q.where(
            or_(
                Lead.first_name.ilike(term),
                Lead.last_name.ilike(term),
                Lead.email.ilike(term),
                Lead.organization_name.ilike(term),
            )
        )
    result = await db.execute(q)
    return [LeadRead.model_validate(lead) for lead in result.scalars().all()]


@router.post("", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
async def create_lead(
    request: Request,
    body: LeadCreate,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> LeadRead:
    lead = Lead(
        source=body.source,
        status="new",
        first_name=body.first_name,
        last_name=body.last_name,
        email=str(body.email),
        phone=body.phone,
        organization_name=body.organization_name,
        provider_type=body.provider_type,
        notes=body.notes,
        lead_data=body.lead_data,
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    await audit.log(
        action="CREATE_LEAD",
        resource_type="lead",
        resource_id=lead.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        user_id=current_user.id,
        extra_context={"email": str(body.email), "source": body.source},
    )
    return LeadRead.model_validate(lead)


@router.get("/stats")
async def lead_stats(
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    total_result = await db.execute(select(func.count()).select_from(Lead))
    total = total_result.scalar() or 0

    new_week_result = await db.execute(
        select(func.count()).select_from(Lead).where(Lead.created_at >= week_ago)
    )
    new_week = new_week_result.scalar() or 0

    converted_result = await db.execute(
        select(func.count()).select_from(Lead).where(Lead.status == "converted")
    )
    converted = converted_result.scalar() or 0

    return {
        "total": total,
        "new_this_week": new_week,
        "converted": converted,
        "conversion_rate": round(converted / total * 100, 1) if total else 0.0,
    }


@router.get("/{lead_id}", response_model=LeadRead)
async def get_lead(
    lead_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LeadRead:
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return LeadRead.model_validate(lead)


@router.patch("/{lead_id}", response_model=LeadRead)
async def update_lead(
    request: Request,
    lead_id: uuid.UUID,
    body: LeadUpdate,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> LeadRead:
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(lead, field, value)
    lead.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(lead)
    await audit.log(
        action="UPDATE_LEAD",
        resource_type="lead",
        resource_id=lead.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        user_id=current_user.id,
        extra_context=body.model_dump(exclude_unset=True),
    )
    return LeadRead.model_validate(lead)


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    request: Request,
    lead_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> None:
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    if lead.source != "manual":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only manually-added leads can be deleted",
        )
    await audit.log(
        action="DELETE_LEAD",
        resource_type="lead",
        resource_id=lead.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        user_id=current_user.id,
        extra_context={"email": lead.email, "source": lead.source},
    )
    await db.delete(lead)
    await db.commit()


@router.post("/{lead_id}/convert", status_code=status.HTTP_200_OK)
async def convert_lead(
    request: Request,
    lead_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> dict:
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    if lead.converted_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lead already converted")
    if lead.is_demo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Demo leads cannot be converted to provider accounts")

    existing = await db.execute(select(User).where(User.email == lead.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )

    temp_password = _gen_password()
    full_name = f"{lead.first_name} {lead.last_name}".strip() or None
    new_user_read = await AdminService(db).create_user(
        UserCreate(email=lead.email, password=temp_password, full_name=full_name, role="provider")
    )

    user_result = await db.execute(select(User).where(User.id == new_user_read.id))
    new_user = user_result.scalar_one()

    checkout_url: str | None = None
    try:
        from app.services import stripe_service
        if stripe_service._configured() and settings.STRIPE_DEPOSIT_PRICE_ID:
            checkout_url = await stripe_service.create_deposit_checkout_link(new_user, db)
    except Exception:
        log.warning("Could not create deposit link for converted lead %s", lead_id, exc_info=True)

    try:
        from app.services import email_service
        await email_service.send_welcome_and_deposit(
            provider_email=lead.email,
            provider_name=full_name or lead.email,
            temp_password=temp_password,
            checkout_url=checkout_url,
            frontend_origin=settings.FRONTEND_ORIGIN,
        )
        new_user.welcome_email_sent_at = datetime.now(timezone.utc)
    except Exception:
        log.warning("Could not send welcome email for converted lead %s", lead_id, exc_info=True)

    lead.converted_user_id = new_user.id
    lead.status = "converted"
    lead.updated_at = datetime.now(timezone.utc)
    await db.commit()

    await audit.log(
        action="CONVERT_LEAD",
        resource_type="lead",
        resource_id=lead.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        user_id=current_user.id,
        extra_context={
            "lead_email": lead.email,
            "new_user_id": str(new_user.id),
            "deposit_link_included": checkout_url is not None,
        },
    )
    return {
        "user_id": str(new_user.id),
        "email": lead.email,
        "checkout_url": checkout_url,
    }

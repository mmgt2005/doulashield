import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import AuditLogger
from app.core.encryption import encrypt_field
from app.dependencies import CurrentUser, get_audit, get_client_ip, get_db, get_user_agent, require_admin
from app.models.billing_provider import BillingProvider
from app.schemas.admin import BillingProviderCreate, BillingProviderRead

router = APIRouter(prefix="/admin/billing-providers", tags=["admin"])


def _to_read(bp: BillingProvider) -> BillingProviderRead:
    return BillingProviderRead(
        id=bp.id,
        name=bp.name,
        npi=bp.npi,
        taxonomy_code=bp.taxonomy_code,
        address=bp.address,
        city=bp.city,
        state=bp.state,
        zip_code=bp.zip_code,
        phone=bp.phone,
        tax_id_connected=bp.tax_id_encrypted is not None,
        created_at=bp.created_at,
    )


@router.get("", response_model=list[BillingProviderRead])
async def list_billing_providers(
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[BillingProviderRead]:
    result = await db.execute(select(BillingProvider).order_by(BillingProvider.name))
    return [_to_read(bp) for bp in result.scalars().all()]


@router.post("", response_model=BillingProviderRead, status_code=status.HTTP_201_CREATED)
async def create_billing_provider(
    request: Request,
    body: BillingProviderCreate,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> BillingProviderRead:
    bp = BillingProvider(
        name=body.name,
        npi=body.npi,
        taxonomy_code=body.taxonomy_code,
        address=body.address,
        city=body.city,
        state=body.state,
        zip_code=body.zip_code,
        phone=body.phone,
        tax_id_encrypted=encrypt_field(body.tax_id) if body.tax_id else None,
    )
    db.add(bp)
    await db.commit()
    await db.refresh(bp)

    await audit.log(
        action="CREATE_BILLING_PROVIDER",
        resource_type="billing_provider",
        resource_id=bp.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        user_id=current_user.id,
        extra_context={"name": bp.name, "npi": bp.npi},
    )
    return _to_read(bp)


@router.put("/{bp_id}", response_model=BillingProviderRead)
async def update_billing_provider(
    request: Request,
    bp_id: uuid.UUID,
    body: BillingProviderCreate,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> BillingProviderRead:
    result = await db.execute(select(BillingProvider).where(BillingProvider.id == bp_id))
    bp = result.scalar_one_or_none()
    if not bp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing provider not found")

    bp.name = body.name
    bp.npi = body.npi
    bp.taxonomy_code = body.taxonomy_code
    bp.address = body.address
    bp.city = body.city
    bp.state = body.state
    bp.zip_code = body.zip_code
    bp.phone = body.phone
    if body.tax_id is not None:
        bp.tax_id_encrypted = encrypt_field(body.tax_id) if body.tax_id else None

    await db.commit()
    await db.refresh(bp)

    await audit.log(
        action="UPDATE_BILLING_PROVIDER",
        resource_type="billing_provider",
        resource_id=bp.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        user_id=current_user.id,
        extra_context={"name": bp.name, "npi": bp.npi},
    )
    return _to_read(bp)


@router.delete("/{bp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_billing_provider(
    request: Request,
    bp_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> None:
    result = await db.execute(select(BillingProvider).where(BillingProvider.id == bp_id))
    bp = result.scalar_one_or_none()
    if not bp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing provider not found")

    await audit.log(
        action="DELETE_BILLING_PROVIDER",
        resource_type="billing_provider",
        resource_id=bp.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        user_id=current_user.id,
        extra_context={"name": bp.name, "npi": bp.npi},
    )
    await db.delete(bp)
    await db.commit()

from __future__ import annotations

import secrets
import string
import uuid
from datetime import datetime, timezone
from typing import Annotated

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from fastapi import Form, UploadFile

from app.core.audit import AuditLogger
from app.core.config import settings
from app.core.encryption import encrypt_field
from app.dependencies import CurrentUser, get_audit, get_current_user, get_db, require_admin, require_billing_admin
from app.models.billing_provider import BillingProvider
from app.models.claim import Claim
from app.models.claim_document import ClaimDocument
from app.models.patient import Patient
from app.models.user import User
from app.schemas.admin import (
    BillingProviderCreate,
    BillingProviderRead,
    BillingProviderUpdate,
    UserCreate,
)
from app.schemas.claim import ClaimDocumentRead, ClaimRead, ManualClaimUpsert
from app.core.security import hash_password
from app.schemas.billing import (
    BillingStatusRead,
    CreateAccountOnlyRequest,
    CreateAndInviteRequest,
    GenerateDepositLinkRequest,
    LinkStripeCustomerRequest,
    SendWelcomeEmailRequest,
    SignEscrowRequest,
    StartSubscriptionRequest,
    UserWithBillingRead,
)
from app.services import email_service, stripe_service
from app.services.admin_service import AdminService

_SPECIAL = "!@#$%^&*"
_POOL = string.ascii_letters + string.digits + _SPECIAL


def _generate_temp_password() -> str:
    while True:
        pwd = "".join(secrets.choice(_POOL) for _ in range(14))
        if (
            any(c.isupper() for c in pwd)
            and any(c.islower() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in _SPECIAL for c in pwd)
        ):
            return pwd

router = APIRouter(tags=["billing"])


def _require_stripe() -> None:
    if not stripe_service._configured():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Stripe not configured")


async def _get_provider(user_id: uuid.UUID, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


# ── Provider endpoints ────────────────────────────────────────────────────────

@router.get("/billing/status", response_model=BillingStatusRead)
async def get_billing_status(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BillingStatusRead:
    user = await _get_provider(current_user.id, db)
    return BillingStatusRead.model_validate(user)


@router.post("/billing/sign-escrow", response_model=BillingStatusRead)
async def sign_escrow(
    body: SignEscrowRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> BillingStatusRead:
    if not body.agreed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Must agree to escrow terms")
    user = await _get_provider(current_user.id, db)
    if user.escrow_agreed_at:
        return BillingStatusRead.model_validate(user)
    user.escrow_agreed_at = datetime.now(timezone.utc)
    user.escrow_agreement_version = stripe_service.ESCROW_AGREEMENT_VERSION
    await db.commit()
    await audit.log(
        action="SIGN_ESCROW_AGREEMENT",
        resource_type="user",
        resource_id=current_user.id,
        user_id=current_user.id,
        ip_address=request.headers.get("X-Forwarded-For", request.client.host if request.client else ""),
        user_agent=request.headers.get("User-Agent", ""),
        extra_context={"version": stripe_service.ESCROW_AGREEMENT_VERSION},
    )
    await db.refresh(user)
    return BillingStatusRead.model_validate(user)


# ── Stripe webhook ────────────────────────────────────────────────────────────

@router.post("/billing/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> dict:
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Webhook not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    event_type: str = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        user_id_str = (data.get("metadata") or {}).get("user_id")
        customer_id = data.get("customer")
        if user_id_str and customer_id:
            try:
                uid = uuid.UUID(user_id_str)
            except ValueError:
                return {"received": True}
            result = await db.execute(select(User).where(User.id == uid))
            user = result.scalar_one_or_none()
            if user:
                user.stripe_customer_id = customer_id
                user.deposit_paid = True
                user.deposit_paid_at = datetime.now(timezone.utc)
                await db.commit()
                await audit.log(
                    action="DEPOSIT_PAID",
                    resource_type="user",
                    resource_id=uid,
                    ip_address="stripe-webhook",
                    user_agent="",
                    extra_context={"stripe_customer_id": customer_id, "checkout_session_id": data.get("id")},
                )
                transfer = await stripe_service.transfer_to_partner(
                    data.get("amount_total", 0),
                    {"type": "deposit", "user_id": user_id_str, "checkout_session_id": data.get("id")},
                )
                if transfer:
                    await audit.log(
                        action="PARTNER_TRANSFER",
                        resource_type="user",
                        resource_id=uid,
                        ip_address="stripe-webhook",
                        user_agent="",
                        extra_context={"transfer_id": transfer["transfer_id"], "amount_cents": transfer["amount"], "reason": "deposit"},
                    )

    elif event_type == "invoice.payment_succeeded":
        sub_id = data.get("subscription")
        amount_paid = data.get("amount_paid", 0)
        if sub_id and amount_paid > 0:
            result = await db.execute(select(User).where(User.stripe_subscription_id == sub_id))
            user = result.scalar_one_or_none()
            if user:
                transfer = await stripe_service.transfer_to_partner(
                    amount_paid,
                    {"type": "subscription", "user_id": str(user.id), "invoice_id": data.get("id")},
                )
                if transfer:
                    await audit.log(
                        action="PARTNER_TRANSFER",
                        resource_type="user",
                        resource_id=user.id,
                        ip_address="stripe-webhook",
                        user_agent="",
                        extra_context={"transfer_id": transfer["transfer_id"], "amount_cents": transfer["amount"], "reason": "subscription"},
                    )

    elif event_type in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"):
        meta = data.get("metadata") or {}
        bp_id_str = meta.get("billing_provider_id")
        user_id_str = meta.get("user_id")
        sub_id = data.get("id")
        new_status = data.get("status")
        if event_type == "customer.subscription.deleted":
            new_status = "canceled"

        if bp_id_str:
            try:
                bp_uuid = uuid.UUID(bp_id_str)
                bp_result = await db.execute(select(BillingProvider).where(BillingProvider.id == bp_uuid))
            except ValueError:
                bp_result = await db.execute(select(BillingProvider).where(BillingProvider.stripe_subscription_id == sub_id))
            bp = bp_result.scalar_one_or_none()
            if bp and new_status:
                bp.subscription_status = new_status
                await db.commit()
        else:
            if user_id_str:
                try:
                    uid = uuid.UUID(user_id_str)
                    result = await db.execute(select(User).where(User.id == uid))
                except ValueError:
                    result = await db.execute(select(User).where(User.stripe_subscription_id == sub_id))
            else:
                result = await db.execute(select(User).where(User.stripe_subscription_id == sub_id))
            user = result.scalar_one_or_none()
            if user and new_status:
                user.subscription_status = new_status
                await db.commit()

    elif event_type == "invoice.payment_failed":
        sub_id = data.get("subscription")
        if sub_id:
            bp_result = await db.execute(select(BillingProvider).where(BillingProvider.stripe_subscription_id == sub_id))
            bp = bp_result.scalar_one_or_none()
            if bp:
                bp.subscription_status = "past_due"
                await db.commit()
            else:
                result = await db.execute(select(User).where(User.stripe_subscription_id == sub_id))
                user = result.scalar_one_or_none()
                if user:
                    user.subscription_status = "past_due"
                    await db.commit()
                    await audit.log(
                        action="SUBSCRIPTION_PAYMENT_FAILED",
                        resource_type="user",
                        resource_id=user.id,
                        ip_address="stripe-webhook",
                        user_agent="",
                        extra_context={"invoice_id": data.get("id")},
                    )

    elif event_type == "payment_intent.payment_failed":
        meta = data.get("metadata") or {}
        if meta.get("type") == "escrow_deduction":
            user_id_str = meta.get("user_id")
            if user_id_str:
                try:
                    uid = uuid.UUID(user_id_str)
                    await audit.log(
                        action="ESCROW_DEDUCTION_FAILED",
                        resource_type="user",
                        resource_id=uid,
                        ip_address="stripe-webhook",
                        user_agent="",
                        extra_context={
                            "payment_intent_id": data.get("id"),
                            "remittance_id": meta.get("remittance_id"),
                        },
                    )
                except ValueError:
                    pass

    return {"received": True}


# ── Admin endpoints ───────────────────────────────────────────────────────────

@router.post("/admin/billing/create-and-invite", status_code=status.HTTP_201_CREATED)
async def create_and_invite(
    body: CreateAndInviteRequest,
    current_admin: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> dict:
    if not email_service._configured():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Email not configured — set RESEND_API_KEY")

    existing = await db.execute(select(User).where(User.email == str(body.email)))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A user with this email already exists")

    role = body.role if body.role in ("provider", "admin", "billing_admin") else "provider"
    temp_password = _generate_temp_password()
    new_user_read = await AdminService(db).create_user(
        UserCreate(email=str(body.email), password=temp_password, full_name=body.full_name, role=role)
    )

    result = await db.execute(select(User).where(User.id == new_user_read.id))
    new_user = result.scalar_one()

    if role == "billing_admin" and body.managed_billing_provider_id:
        new_user.managed_billing_provider_id = body.managed_billing_provider_id

    checkout_url: str | None = None
    if role == "provider" and stripe_service._configured() and settings.STRIPE_DEPOSIT_PRICE_ID:
        try:
            checkout_url = await stripe_service.create_deposit_checkout_link(new_user, db)
        except Exception:
            checkout_url = None

    await email_service.send_welcome_and_deposit(
        provider_email=str(body.email),
        provider_name=body.full_name or str(body.email),
        temp_password=temp_password,
        checkout_url=checkout_url,
        frontend_origin=settings.FRONTEND_ORIGIN,
    )

    new_user.welcome_email_sent_at = datetime.now(timezone.utc)
    await db.commit()

    await audit.log(
        action="CREATE_AND_INVITE_PROVIDER",
        resource_type="user",
        resource_id=new_user_read.id,
        user_id=current_admin.id,
        ip_address=request.headers.get("X-Forwarded-For", request.client.host if request.client else ""),
        user_agent=request.headers.get("User-Agent", ""),
        extra_context={"email": str(body.email), "role": role, "deposit_link_included": checkout_url is not None},
    )
    return {"user_id": str(new_user_read.id), "email": str(body.email), "sent_to": str(body.email)}


@router.post("/admin/billing/create-account-only", status_code=status.HTTP_201_CREATED)
async def create_account_only(
    body: CreateAccountOnlyRequest,
    current_admin: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> dict:
    existing = await db.execute(select(User).where(User.email == str(body.email)))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A user with this email already exists")

    role = body.role if body.role in ("provider", "admin", "billing_admin") else "provider"
    temp_password = _generate_temp_password()
    new_user_read = await AdminService(db).create_user(
        UserCreate(email=str(body.email), password=temp_password, full_name=body.full_name, role=role)
    )
    if role == "billing_admin" and body.managed_billing_provider_id:
        result_u = await db.execute(select(User).where(User.id == new_user_read.id))
        created = result_u.scalar_one()
        created.managed_billing_provider_id = body.managed_billing_provider_id
        await db.commit()

    await audit.log(
        action="CREATE_PROVIDER_ACCOUNT_ONLY",
        resource_type="user",
        resource_id=new_user_read.id,
        user_id=current_admin.id,
        ip_address=request.headers.get("X-Forwarded-For", request.client.host if request.client else ""),
        user_agent=request.headers.get("User-Agent", ""),
        extra_context={"email": str(body.email), "role": role},
    )
    return {"user_id": str(new_user_read.id), "email": str(body.email), "temp_password": temp_password}


@router.post("/admin/billing/send-welcome-email")
async def send_welcome_email(
    body: SendWelcomeEmailRequest,
    current_admin: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> dict:
    if not email_service._configured():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Email not configured — set RESEND_API_KEY")

    provider = await _get_provider(body.provider_user_id, db)

    temp_password = _generate_temp_password()
    provider.password_hash = hash_password(temp_password)  # type: ignore[assignment]
    await db.commit()

    checkout_url: str | None = None
    if provider.role == "provider" and stripe_service._configured() and settings.STRIPE_DEPOSIT_PRICE_ID:
        try:
            checkout_url = await stripe_service.create_deposit_checkout_link(provider, db)
        except Exception:
            checkout_url = None

    try:
        await email_service.send_welcome_and_deposit(
            provider_email=provider.email,
            provider_name=provider.full_name or provider.email,
            temp_password=temp_password,
            checkout_url=checkout_url,
            frontend_origin=settings.FRONTEND_ORIGIN,
            role=provider.role,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Password reset succeeded but email delivery failed: {exc}",
        )

    try:
        provider.welcome_email_sent_at = datetime.now(timezone.utc)
        await db.commit()
    except Exception:
        pass

    await audit.log(
        action="SEND_WELCOME_EMAIL",
        resource_type="user",
        resource_id=provider.id,
        user_id=current_admin.id,
        ip_address=request.headers.get("X-Forwarded-For", request.client.host if request.client else ""),
        user_agent=request.headers.get("User-Agent", ""),
        extra_context={"sent_to": provider.email, "deposit_link_included": checkout_url is not None},
    )
    return {"sent_to": provider.email}


@router.post("/admin/billing/generate-deposit-link")
async def generate_deposit_link(
    body: GenerateDepositLinkRequest,
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> dict:
    _require_stripe()
    provider = await _get_provider(body.provider_user_id, db)
    if provider.deposit_paid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Deposit already paid")
    if not email_service._configured():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Email not configured")

    checkout_url = await stripe_service.create_deposit_checkout_link(provider, db)
    await email_service.send_deposit_link(
        provider_email=provider.email,
        provider_name=provider.full_name or provider.email,
        checkout_url=checkout_url,
    )
    await audit.log(
        action="DEPOSIT_LINK_SENT",
        resource_type="user",
        resource_id=provider.id,
        ip_address=request.headers.get("X-Forwarded-For", request.client.host if request.client else ""),
        user_agent=request.headers.get("User-Agent", ""),
        extra_context={"sent_to": provider.email},
    )
    return {"sent_to": provider.email, "checkout_url": checkout_url}


@router.post("/admin/billing/link-stripe-customer")
async def link_stripe_customer(
    body: LinkStripeCustomerRequest,
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> dict:
    provider = await _get_provider(body.provider_user_id, db)
    provider.stripe_customer_id = body.stripe_customer_id
    provider.deposit_paid = True
    provider.deposit_paid_at = datetime.now(timezone.utc)
    await db.commit()
    await audit.log(
        action="MANUAL_CUSTOMER_LINK",
        resource_type="user",
        resource_id=provider.id,
        ip_address=request.headers.get("X-Forwarded-For", request.client.host if request.client else ""),
        user_agent=request.headers.get("User-Agent", ""),
        extra_context={"stripe_customer_id": body.stripe_customer_id},
    )
    return {"stripe_customer_id": body.stripe_customer_id, "deposit_paid": True}


@router.post("/admin/billing/start-subscription")
async def start_subscription(
    body: StartSubscriptionRequest,
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> dict:
    _require_stripe()
    provider = await _get_provider(body.provider_user_id, db)
    if provider.subscription_status in ("active", "trialing"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subscription already active")
    result = await stripe_service.start_subscription(provider, db)
    await audit.log(
        action="START_SUBSCRIPTION",
        resource_type="user",
        resource_id=provider.id,
        ip_address=request.headers.get("X-Forwarded-For", request.client.host if request.client else ""),
        user_agent=request.headers.get("User-Agent", ""),
        extra_context=result,
    )
    return result


@router.get("/admin/billing/users", response_model=list[UserWithBillingRead])
async def list_users_with_billing(
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[UserWithBillingRead]:
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return [UserWithBillingRead.model_validate(u) for u in result.scalars().all()]


# ── Billing Provider endpoints ────────────────────────────────────────────────

def _bp_to_read(bp: BillingProvider, provider_count: int = 0) -> BillingProviderRead:
    r = BillingProviderRead.model_validate(bp)
    r.provider_count = provider_count
    r.availity_connected = bool(bp.availity_client_id_encrypted and bp.availity_client_secret_encrypted)
    r.availity_npi = bp.availity_npi
    return r


async def _get_billing_provider(bp_id: uuid.UUID, db: AsyncSession) -> BillingProvider:
    result = await db.execute(select(BillingProvider).where(BillingProvider.id == bp_id))
    bp = result.scalar_one_or_none()
    if not bp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing provider not found")
    return bp


async def _get_managed_bp_id(user_id: uuid.UUID, db: AsyncSession) -> uuid.UUID | None:
    """Look up a billing admin's managed_billing_provider_id from the DB."""
    result = await db.execute(
        select(User.managed_billing_provider_id).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


@router.get("/admin/billing-providers", response_model=list[BillingProviderRead])
async def list_billing_providers(
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[BillingProviderRead]:
    result = await db.execute(select(BillingProvider).order_by(BillingProvider.name))
    bps = result.scalars().all()
    reads = []
    for bp in bps:
        count_result = await db.execute(
            select(User).where(User.billing_provider_id == bp.id)
        )
        provider_count = len(count_result.scalars().all())
        reads.append(_bp_to_read(bp, provider_count))
    return reads


@router.post("/admin/billing-providers", response_model=BillingProviderRead, status_code=status.HTTP_201_CREATED)
async def create_billing_provider(
    body: BillingProviderCreate,
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> BillingProviderRead:
    bp = BillingProvider(**body.model_dump())
    db.add(bp)
    await db.commit()
    await db.refresh(bp)
    await audit.log(
        action="CREATE_BILLING_PROVIDER",
        resource_type="billing_provider",
        resource_id=bp.id,
        ip_address=request.headers.get("X-Forwarded-For", request.client.host if request.client else ""),
        user_agent=request.headers.get("User-Agent", ""),
        extra_context={"name": bp.name},
    )

    # Send onboarding email to billing admin if one is linked
    admin_result = await db.execute(
        select(User).where(
            User.managed_billing_provider_id == bp.id,
            User.is_active.is_(True),
        )
    )
    billing_admin = admin_result.scalar_one_or_none()
    if billing_admin and billing_admin.email:
        try:
            await email_service.send_agency_onboarding_email(
                admin_email=billing_admin.email,
                admin_name=billing_admin.full_name or billing_admin.email,
                agency_name=bp.name,
                agency_group_npi=bp.group_npi or "",
                frontend_origin=settings.FRONTEND_ORIGIN,
            )
        except Exception:
            pass  # email failure must not break agency creation

    return _bp_to_read(bp, 0)


@router.put("/admin/billing-providers/{bp_id}", response_model=BillingProviderRead)
async def update_billing_provider(
    bp_id: uuid.UUID,
    body: BillingProviderUpdate,
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BillingProviderRead:
    bp = await _get_billing_provider(bp_id, db)
    update_data = body.model_dump(exclude_none=True)
    # Handle Availity credential encryption (strip plain fields, store encrypted)
    if "availity_client_id" in update_data:
        bp.availity_client_id_encrypted = encrypt_field(update_data.pop("availity_client_id"))
    else:
        update_data.pop("availity_client_id", None)
    if "availity_client_secret" in update_data:
        bp.availity_client_secret_encrypted = encrypt_field(update_data.pop("availity_client_secret"))
    else:
        update_data.pop("availity_client_secret", None)
    for field, value in update_data.items():
        setattr(bp, field, value)
    await db.commit()
    await db.refresh(bp)
    count_result = await db.execute(select(User).where(User.billing_provider_id == bp.id))
    provider_count = len(count_result.scalars().all())
    return _bp_to_read(bp, provider_count)


@router.delete("/admin/billing-providers/{bp_id}", response_class=Response)
async def delete_billing_provider(
    bp_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    bp = await _get_billing_provider(bp_id, db)
    count_result = await db.execute(select(User).where(User.billing_provider_id == bp.id))
    if count_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete billing provider with assigned providers",
        )
    await db.delete(bp)
    await db.commit()
    return Response(status_code=204)


@router.post("/admin/billing-providers/{bp_id}/assign-provider")
async def assign_provider_to_billing_provider(
    bp_id: uuid.UUID,
    body: dict,
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> dict:
    bp = await _get_billing_provider(bp_id, db)
    provider_user_id = body.get("provider_user_id")
    if not provider_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="provider_user_id required")
    try:
        uid = uuid.UUID(str(provider_user_id))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid provider_user_id")
    provider = await _get_provider(uid, db)
    # Cancel individual Stripe subscription when moving to an agency
    cancelled_sub: dict | None = None
    if (
        provider.stripe_subscription_id
        and provider.subscription_status in ("active", "trialing")
        and _configured()
    ):
        cancelled_sub = await stripe_service.cancel_subscription(provider, db)
    provider.billing_provider_id = bp.id
    await db.commit()
    await audit.log(
        action="ASSIGN_BILLING_PROVIDER",
        resource_type="user",
        resource_id=provider.id,
        ip_address=request.headers.get("X-Forwarded-For", request.client.host if request.client else ""),
        user_agent=request.headers.get("User-Agent", ""),
        extra_context={
            "billing_provider_id": str(bp.id),
            "billing_provider_name": bp.name,
            **({"cancelled_subscription": cancelled_sub} if cancelled_sub else {}),
        },
    )
    return {
        "provider_user_id": str(provider.id),
        "billing_provider_id": str(bp.id),
        **({"subscription_cancelled": True} if cancelled_sub and cancelled_sub.get("cancelled") else {}),
    }


@router.post("/admin/billing-providers/{bp_id}/start-subscription")
async def start_billing_provider_subscription(
    bp_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> dict:
    _require_stripe()
    bp = await _get_billing_provider(bp_id, db)
    if bp.subscription_status in ("active", "trialing"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subscription already active")
    result = await db.execute(select(User).where(User.billing_provider_id == bp.id))
    providers = result.scalars().all()
    if not providers:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No providers assigned to this billing provider")
    representative = providers[0]
    result = await stripe_service.start_subscription(representative, db)
    await audit.log(
        action="START_BILLING_PROVIDER_SUBSCRIPTION",
        resource_type="billing_provider",
        resource_id=bp.id,
        ip_address=request.headers.get("X-Forwarded-For", request.client.host if request.client else ""),
        user_agent=request.headers.get("User-Agent", ""),
        extra_context=result,
    )
    return result


@router.get("/admin/stats/billing-providers")
async def billing_provider_stats(
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict]:
    from sqlalchemy import func as sqlfunc, case, text as sqlt
    rows = await db.execute(
        sqlt("""
            SELECT
                bp.id::text AS billing_provider_id,
                bp.name,
                bp.subscription_status,
                COUNT(DISTINCT u.id) AS provider_count,
                COUNT(c.id) AS total_claims,
                COALESCE(SUM(c.billed_amount), 0) AS total_billed,
                COALESCE(SUM(c.paid_amount), 0) AS total_paid,
                ROUND(
                    100.0 * SUM(CASE WHEN c.status = 'denied' THEN 1 ELSE 0 END)
                    / NULLIF(COUNT(c.id), 0),
                    1
                ) AS denial_rate
            FROM public.billing_providers bp
            LEFT JOIN public.users u ON u.billing_provider_id = bp.id
            LEFT JOIN public.claims c ON c.provider_id = u.id
            GROUP BY bp.id, bp.name, bp.subscription_status
            ORDER BY bp.name
        """)
    )
    return [dict(r) for r in rows.mappings()]


# ── Billing admin scoped endpoints ────────────────────────────────────────────

@router.get("/billing-admin/claims", response_model=list[ClaimRead])
async def list_billing_admin_claims(
    current_user: Annotated[CurrentUser, Depends(require_billing_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    bp_id: uuid.UUID | None = None,
) -> list[ClaimRead]:
    """Returns all claims across all providers assigned to the billing admin's managed agency.
    Admins may pass ?bp_id=<uuid> to view any agency's claim queue."""
    managed_bp_id = None if current_user.role == "admin" else await _get_managed_bp_id(current_user.id, db)
    effective_bp_id = bp_id if (current_user.role == "admin" and bp_id) else managed_bp_id
    if not effective_bp_id:
        return []
    providers_result = await db.execute(
        select(User.id).where(User.billing_provider_id == effective_bp_id)
    )
    provider_ids = [row.id for row in providers_result]
    if not provider_ids:
        return []
    claims_result = await db.execute(
        select(Claim)
        .join(Patient, Claim.patient_id == Patient.id)
        .where(Claim.provider_id.in_(provider_ids))
        .where(Patient.is_demo == False)  # noqa: E712
        .order_by(Claim.created_at.desc())
    )
    return [ClaimRead.model_validate(c) for c in claims_result.scalars().all()]


@router.get("/billing-admin/providers", response_model=list[dict])
async def list_billing_admin_providers(
    current_user: Annotated[CurrentUser, Depends(require_billing_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    bp_id: uuid.UUID | None = None,
) -> list[dict]:
    """Returns all providers assigned to the billing admin's managed agency.
    Admins may pass ?bp_id=<uuid> to view any agency's providers."""
    managed_bp_id = None if current_user.role == "admin" else await _get_managed_bp_id(current_user.id, db)
    effective_bp_id = bp_id if (current_user.role == "admin" and bp_id) else managed_bp_id
    if not effective_bp_id:
        return []
    result = await db.execute(
        select(User).where(
            User.billing_provider_id == effective_bp_id,
            User.is_active.is_(True),
        ).order_by(User.full_name)
    )
    return [
        {"id": str(u.id), "email": u.email, "full_name": u.full_name, "npi": u.npi}
        for u in result.scalars().all()
    ]


@router.get("/billing-admin/agency-settings", response_model=BillingProviderRead)
async def get_agency_settings(
    current_user: Annotated[CurrentUser, Depends(require_billing_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    bp_id: uuid.UUID | None = None,
) -> BillingProviderRead:
    """Returns the billing admin's managed agency settings (never returns raw Availity secrets).
    Admins may pass ?bp_id=<uuid> to view any agency's settings."""
    managed_bp_id = None if current_user.role == "admin" else await _get_managed_bp_id(current_user.id, db)
    effective_bp_id = bp_id if (current_user.role == "admin" and bp_id) else managed_bp_id
    if not effective_bp_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No managed agency found")
    bp = await _get_billing_provider(effective_bp_id, db)
    count_result = await db.execute(select(User).where(User.billing_provider_id == bp.id))
    provider_count = len(count_result.scalars().all())
    return _bp_to_read(bp, provider_count)


@router.patch("/billing-admin/agency-settings", response_model=BillingProviderRead)
async def update_agency_settings(
    body: BillingProviderUpdate,
    current_user: Annotated[CurrentUser, Depends(require_billing_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
    bp_id: uuid.UUID | None = None,
) -> BillingProviderRead:
    """Allows a billing admin (or admin) to update an agency's Availity credentials and other settings."""
    managed_bp_id = None if current_user.role == "admin" else await _get_managed_bp_id(current_user.id, db)
    effective_bp_id = bp_id if (current_user.role == "admin" and bp_id) else managed_bp_id
    if not effective_bp_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No managed agency found")
    bp = await _get_billing_provider(effective_bp_id, db)
    update_data = body.model_dump(exclude_none=True)
    if "availity_client_id" in update_data:
        bp.availity_client_id_encrypted = encrypt_field(update_data.pop("availity_client_id"))
    else:
        update_data.pop("availity_client_id", None)
    if "availity_client_secret" in update_data:
        bp.availity_client_secret_encrypted = encrypt_field(update_data.pop("availity_client_secret"))
    else:
        update_data.pop("availity_client_secret", None)
    for field, value in update_data.items():
        if hasattr(bp, field):
            setattr(bp, field, value)
    await db.commit()
    await db.refresh(bp)
    await audit.log(
        action="UPDATE_AGENCY_AVAILITY",
        resource_type="billing_provider",
        resource_id=bp.id,
        user_id=current_user.id,
        ip_address=request.headers.get("X-Forwarded-For", request.client.host if request.client else ""),
        user_agent=request.headers.get("User-Agent", ""),
        extra_context={"availity_connected": bool(bp.availity_client_id_encrypted and bp.availity_client_secret_encrypted)},
    )
    count_result = await db.execute(select(User).where(User.billing_provider_id == bp.id))
    provider_count = len(count_result.scalars().all())
    return _bp_to_read(bp, provider_count)


@router.post("/billing-admin/claims/{claim_id}/submit", response_model=ClaimRead)
async def submit_agency_claim(
    claim_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(require_billing_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> ClaimRead:
    """Billing admin reviews a queued claim and submits it to Availity using agency credentials."""
    from app.core.encryption import decrypt_field
    from app.services.availity_client import AvailityClient

    # Load the claim
    claim_result = await db.execute(select(Claim).where(Claim.id == claim_id))
    claim = claim_result.scalar_one_or_none()
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    if claim.status != "pending_billing_review":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Claim is not in pending_billing_review status (current: {claim.status})",
        )

    # Resolve which agency is submitting this claim
    provider_result = await db.execute(select(User).where(User.id == claim.provider_id))
    provider = provider_result.scalar_one_or_none()
    if not provider or not provider.billing_provider_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Claim provider has no assigned agency")

    # Admins may submit on behalf of any agency; billing_admins only their own
    if current_user.role == "admin":
        effective_bp_id = provider.billing_provider_id
    else:
        managed_bp_id = await _get_managed_bp_id(current_user.id, db)
        if not managed_bp_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No managed agency")
        if provider.billing_provider_id != managed_bp_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Claim does not belong to your agency")
        effective_bp_id = managed_bp_id

    # Load agency
    bp = await _get_billing_provider(effective_bp_id, db)
    if not bp.availity_client_id_encrypted or not bp.availity_client_secret_encrypted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agency Availity credentials not configured — add them in Agency Settings",
        )

    # Submit via agency credentials
    client = AvailityClient(
        decrypt_field(bp.availity_client_id_encrypted),
        decrypt_field(bp.availity_client_secret_encrypted),
        str(bp.id),
    )

    # Use the claim_data stored at queue time (already built with full 837P shape)
    claim_body = claim.claim_data or {}
    # Inject agency billing provider override (Box 33a)
    claim_body["billingProvider"] = {
        "npi": bp.group_npi or "",
        "organizationName": bp.name,
    }

    raw_response = await client.post("/claims", body=claim_body)

    claim.availity_claim_id = raw_response.get("claimId")
    claim.status = raw_response.get("status", "submitted")
    claim.submitted_at = datetime.now(timezone.utc)
    claim.raw_response = raw_response
    await db.commit()
    await db.refresh(claim)

    await audit.log(
        action="SUBMIT_AGENCY_CLAIM",
        resource_type="claim",
        resource_id=claim.id,
        user_id=current_user.id,
        ip_address=request.headers.get("X-Forwarded-For", request.client.host if request.client else ""),
        user_agent=request.headers.get("User-Agent", ""),
        extra_context={"billing_provider_id": str(bp.id), "provider_id": str(claim.provider_id)},
    )
    return ClaimRead.model_validate(claim)


@router.put("/billing-admin/claims/{claim_id}/status", response_model=ClaimRead)
async def update_agency_claim_status(
    claim_id: uuid.UUID,
    body: ManualClaimUpsert,
    current_user: Annotated[CurrentUser, Depends(require_billing_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
) -> ClaimRead:
    """Billing admin logs a manual submission or updates status for a queued claim."""
    claim_result = await db.execute(select(Claim).where(Claim.id == claim_id))
    claim = claim_result.scalar_one_or_none()
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    provider_result = await db.execute(select(User).where(User.id == claim.provider_id))
    provider = provider_result.scalar_one_or_none()
    if not provider or not provider.billing_provider_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Claim provider has no assigned agency")

    if current_user.role == "admin":
        effective_bp_id = provider.billing_provider_id
    else:
        managed_bp_id = await _get_managed_bp_id(current_user.id, db)
        if not managed_bp_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No managed agency")
        if provider.billing_provider_id != managed_bp_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Claim does not belong to your agency")
        effective_bp_id = managed_bp_id

    claim.status = body.status
    claim.is_manual = True
    if body.paid_amount is not None:
        claim.paid_amount = body.paid_amount
    if body.denial_reason is not None:
        claim.denial_reason = body.denial_reason
    if body.status == "submitted":
        claim.submitted_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(claim)

    await audit.log(
        action="MANUAL_STATUS_UPDATE",
        resource_type="claim",
        resource_id=claim.id,
        user_id=current_user.id,
        ip_address=request.headers.get("X-Forwarded-For", request.client.host if request.client else ""),
        user_agent=request.headers.get("User-Agent", ""),
        extra_context={"status": body.status, "billing_provider_id": str(effective_bp_id)},
    )
    return ClaimRead.model_validate(claim)


@router.post("/billing-admin/claims/{claim_id}/documents", response_model=ClaimDocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_claim_document(
    claim_id: uuid.UUID,
    file: UploadFile,
    current_user: Annotated[CurrentUser, Depends(require_billing_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    request: Request,
    document_type: Annotated[str, Form()] = "other",
) -> ClaimDocumentRead:
    """Billing admin uploads a supporting document (prior auth, eligibility, EOB received) to a claim."""
    from app.services.ocr_service import store_image

    _MAX_BYTES = 20 * 1024 * 1024
    _ALLOWED_TYPES = {"image/jpeg", "image/png", "application/pdf"}

    content_type = file.content_type or ""
    if content_type not in _ALLOWED_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only JPEG, PNG, or PDF files are accepted.")

    content_bytes = await file.read()
    if len(content_bytes) > _MAX_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File must be under 20 MB.")

    claim_result = await db.execute(select(Claim).where(Claim.id == claim_id))
    claim = claim_result.scalar_one_or_none()
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    provider_result = await db.execute(select(User).where(User.id == claim.provider_id))
    provider = provider_result.scalar_one_or_none()
    if not provider or not provider.billing_provider_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Claim provider has no assigned agency")

    if current_user.role != "admin":
        managed_bp_id = await _get_managed_bp_id(current_user.id, db)
        if not managed_bp_id or provider.billing_provider_id != managed_bp_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Claim does not belong to your agency")

    file_path = await store_image(
        content_bytes, content_type, None, current_user.id, f"claim-doc-{claim_id}"
    )

    doc = ClaimDocument(
        claim_id=claim_id,
        uploaded_by=current_user.id,
        file_path=file_path,
        file_name=file.filename or "document",
        document_type=document_type,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    await audit.log(
        action="UPLOAD_CLAIM_DOCUMENT",
        resource_type="claim",
        resource_id=claim_id,
        user_id=current_user.id,
        ip_address=request.headers.get("X-Forwarded-For", request.client.host if request.client else ""),
        user_agent=request.headers.get("User-Agent", ""),
        extra_context={"file_name": doc.file_name, "document_type": document_type},
    )

    return ClaimDocumentRead.model_validate(doc)

from __future__ import annotations

import secrets
import string
import uuid
from datetime import datetime, timezone
from typing import Annotated

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import AuditLogger
from app.core.config import settings
from app.dependencies import CurrentUser, get_audit, get_current_user, get_db, require_admin, require_billing_admin
from app.models.billing_provider import BillingProvider
from app.models.claim import Claim
from app.models.user import User
from app.schemas.admin import (
    BillingProviderCreate,
    BillingProviderRead,
    BillingProviderUpdate,
    UserCreate,
)
from app.schemas.claim import ClaimRead
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

    role = body.role if body.role in ("provider", "admin") else "provider"
    temp_password = _generate_temp_password()
    new_user_read = await AdminService(db).create_user(
        UserCreate(email=str(body.email), password=temp_password, full_name=body.full_name, role=role)
    )

    result = await db.execute(select(User).where(User.id == new_user_read.id))
    new_user = result.scalar_one()

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

async def _get_billing_provider(bp_id: uuid.UUID, db: AsyncSession) -> BillingProvider:
    result = await db.execute(select(BillingProvider).where(BillingProvider.id == bp_id))
    bp = result.scalar_one_or_none()
    if not bp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing provider not found")
    return bp


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
        r = BillingProviderRead.model_validate(bp)
        r.provider_count = provider_count
        reads.append(r)
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
    r = BillingProviderRead.model_validate(bp)
    r.provider_count = 0
    return r


@router.put("/admin/billing-providers/{bp_id}", response_model=BillingProviderRead)
async def update_billing_provider(
    bp_id: uuid.UUID,
    body: BillingProviderUpdate,
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BillingProviderRead:
    bp = await _get_billing_provider(bp_id, db)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(bp, field, value)
    await db.commit()
    await db.refresh(bp)
    count_result = await db.execute(select(User).where(User.billing_provider_id == bp.id))
    provider_count = len(count_result.scalars().all())
    r = BillingProviderRead.model_validate(bp)
    r.provider_count = provider_count
    return r


@router.delete("/admin/billing-providers/{bp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_billing_provider(
    bp_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    bp = await _get_billing_provider(bp_id, db)
    count_result = await db.execute(select(User).where(User.billing_provider_id == bp.id))
    if count_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete billing provider with assigned providers",
        )
    await db.delete(bp)
    await db.commit()


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
    provider.billing_provider_id = bp.id
    await db.commit()
    await audit.log(
        action="ASSIGN_BILLING_PROVIDER",
        resource_type="user",
        resource_id=provider.id,
        ip_address=request.headers.get("X-Forwarded-For", request.client.host if request.client else ""),
        user_agent=request.headers.get("User-Agent", ""),
        extra_context={"billing_provider_id": str(bp.id), "billing_provider_name": bp.name},
    )
    return {"provider_user_id": str(provider.id), "billing_provider_id": str(bp.id)}


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
) -> list[ClaimRead]:
    """Returns all claims across all providers assigned to the billing admin's managed agency."""
    if not current_user.managed_billing_provider_id:
        return []
    providers_result = await db.execute(
        select(User.id).where(User.billing_provider_id == current_user.managed_billing_provider_id)
    )
    provider_ids = [row.id for row in providers_result]
    if not provider_ids:
        return []
    claims_result = await db.execute(
        select(Claim)
        .where(Claim.provider_id.in_(provider_ids))
        .order_by(Claim.created_at.desc())
    )
    return [ClaimRead.model_validate(c) for c in claims_result.scalars().all()]


@router.get("/billing-admin/providers", response_model=list[dict])
async def list_billing_admin_providers(
    current_user: Annotated[CurrentUser, Depends(require_billing_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict]:
    """Returns all providers assigned to the billing admin's managed agency."""
    if not current_user.managed_billing_provider_id:
        return []
    result = await db.execute(
        select(User).where(
            User.billing_provider_id == current_user.managed_billing_provider_id,
            User.is_active.is_(True),
        ).order_by(User.full_name)
    )
    return [
        {"id": str(u.id), "email": u.email, "full_name": u.full_name, "npi": u.npi}
        for u in result.scalars().all()
    ]

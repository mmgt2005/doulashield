from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import AuditLogger
from app.core.config import settings
from app.dependencies import CurrentUser, get_audit, get_current_user, get_db, require_admin
from app.models.user import User
from app.schemas.billing import (
    BillingStatusRead,
    GenerateDepositLinkRequest,
    LinkStripeCustomerRequest,
    SignEscrowRequest,
    StartSubscriptionRequest,
    UserWithBillingRead,
)
from app.services import email_service, stripe_service

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

    elif event_type in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"):
        user_id_str = (data.get("metadata") or {}).get("user_id")
        sub_id = data.get("id")
        new_status = data.get("status")
        if event_type == "customer.subscription.deleted":
            new_status = "canceled"

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

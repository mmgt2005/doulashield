from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal

import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.billing_provider import BillingProvider
from app.models.escrow_deduction import EscrowDeduction
from app.models.user import User

ESCROW_AGREEMENT_VERSION = "1.0"
DEFERRED_BALANCE = Decimal("400.00")


def _configured() -> bool:
    return bool(settings.STRIPE_SECRET_KEY)


def _init() -> None:
    stripe.api_key = settings.STRIPE_SECRET_KEY


async def get_or_create_customer(user: User, db: AsyncSession) -> str:
    if user.stripe_customer_id:
        return user.stripe_customer_id
    _init()
    customer = await asyncio.to_thread(
        stripe.Customer.create,
        email=user.email,
        name=user.full_name or user.email,
        metadata={"user_id": str(user.id)},
    )
    user.stripe_customer_id = customer.id
    await db.commit()
    return customer.id


async def create_deposit_checkout_link(provider: User, db: AsyncSession) -> str:
    _init()
    customer_id = await get_or_create_customer(provider, db)
    session = await asyncio.to_thread(
        stripe.checkout.Session.create,
        customer=customer_id,
        mode="payment",
        line_items=[{"price": settings.STRIPE_DEPOSIT_PRICE_ID, "quantity": 1}],
        payment_intent_data={"setup_future_usage": "off_session"},
        metadata={"user_id": str(provider.id)},
        success_url=f"{settings.FRONTEND_ORIGIN}/admin/users?deposit=success",
        cancel_url=f"{settings.FRONTEND_ORIGIN}/admin/users",
    )
    return session.url


async def start_subscription(provider: User, db: AsyncSession) -> dict:
    _init()
    if provider.billing_provider_id and provider.billing_provider:
        bp = provider.billing_provider
        if not bp.stripe_customer_id:
            customer = await asyncio.to_thread(
                stripe.Customer.create,
                email=provider.email,
                name=bp.name,
                metadata={"billing_provider_id": str(bp.id)},
            )
            bp.stripe_customer_id = customer.id

        seat_price = settings.STRIPE_BILLING_PROVIDER_SEAT_PRICE_ID
        if seat_price:
            from sqlalchemy import func
            from sqlalchemy.future import select as _select
            count_result = await db.execute(
                _select(func.count()).select_from(User).where(User.billing_provider_id == bp.id)
            )
            seat_count = count_result.scalar() or 0
            quantity = max(3, seat_count)
            sub = await asyncio.to_thread(
                stripe.Subscription.create,
                customer=bp.stripe_customer_id,
                items=[{"price": seat_price, "quantity": quantity}],
                collection_method="send_invoice",
                days_until_due=30,
                metadata={"billing_provider_id": str(bp.id)},
            )
        else:
            agency_price = settings.STRIPE_AGENCY_MONTHLY_PRICE_ID or settings.STRIPE_MONTHLY_PRICE_ID
            sub = await asyncio.to_thread(
                stripe.Subscription.create,
                customer=bp.stripe_customer_id,
                items=[{"price": agency_price}],
                collection_method="send_invoice",
                days_until_due=30,
                metadata={"billing_provider_id": str(bp.id)},
            )

        bp.stripe_subscription_id = sub.id
        bp.subscription_status = sub.status
        await db.commit()
        result: dict = {"subscription_id": sub.id, "status": sub.status}
        if seat_price:
            result["seat_quantity"] = quantity
            result["monthly_total_cents"] = quantity * 5500
        return result

    customer_id = await get_or_create_customer(provider, db)
    sub = await asyncio.to_thread(
        stripe.Subscription.create,
        customer=customer_id,
        items=[{"price": settings.STRIPE_MONTHLY_PRICE_ID}],
        metadata={"user_id": str(provider.id)},
    )
    provider.stripe_subscription_id = sub.id
    provider.subscription_status = sub.status
    await db.commit()
    return {"subscription_id": sub.id, "status": sub.status}


async def update_billing_provider_seat_quantity(
    bp: BillingProvider, provider_count: int, db: AsyncSession
) -> dict | None:
    """Update the subscription seat quantity when providers are assigned or removed.
    Always enforces a minimum of 3 seats ($165/month floor). Also syncs the
    enrollment tier item if active so both lines stay at the same quantity."""
    if not bp.stripe_subscription_id or not _configured():
        return None
    if not settings.STRIPE_BILLING_PROVIDER_SEAT_PRICE_ID:
        return None
    _init()
    quantity = max(3, provider_count)
    sub = await asyncio.to_thread(stripe.Subscription.retrieve, bp.stripe_subscription_id)
    # Find the seat item by price ID — do not use positional index since the enrollment
    # tier item may also be present on the same subscription.
    seat_item = next(
        (i for i in sub["items"]["data"]
         if i["price"]["id"] == settings.STRIPE_BILLING_PROVIDER_SEAT_PRICE_ID),
        None,
    )
    if not seat_item:
        return None
    await asyncio.to_thread(stripe.SubscriptionItem.modify, seat_item["id"], quantity=quantity)
    if bp.enrollment_tier_stripe_item_id:
        await asyncio.to_thread(
            stripe.SubscriptionItem.modify,
            bp.enrollment_tier_stripe_item_id,
            quantity=quantity,
        )
    return {"item_id": seat_item["id"], "quantity": quantity, "monthly_total_cents": quantity * 5500}


async def enable_enrollment_tier(bp: BillingProvider, provider_count: int, db: AsyncSession) -> dict:
    """Add the enrollment tier as a second subscription item at the current seat quantity."""
    _init()
    quantity = max(3, provider_count)
    item = await asyncio.to_thread(
        stripe.SubscriptionItem.create,
        subscription=bp.stripe_subscription_id,
        price=settings.STRIPE_ENROLLMENT_TIER_PRICE_ID,
        quantity=quantity,
    )
    bp.enrollment_tier_enabled = True
    bp.enrollment_tier_stripe_item_id = item["id"]
    await db.commit()
    return {"enrollment_tier_item_id": item["id"], "quantity": quantity}


async def create_customer_portal_session(stripe_customer_id: str) -> str | None:
    """Return a Stripe Billing Portal URL for the customer to manage their subscription.
    Returns None if the portal is not configured in Stripe."""
    _init()
    try:
        session = await asyncio.to_thread(
            stripe.billing_portal.Session.create,
            customer=stripe_customer_id,
            return_url=f"{settings.FRONTEND_ORIGIN}/billing-admin/settings",
        )
        return session.url
    except stripe.InvalidRequestError:
        return None


async def disable_enrollment_tier(bp: BillingProvider, db: AsyncSession) -> dict:
    """Remove the enrollment tier subscription item with proration credit."""
    _init()
    await asyncio.to_thread(
        stripe.SubscriptionItem.delete,
        bp.enrollment_tier_stripe_item_id,
        proration_behavior="create_prorations",
    )
    bp.enrollment_tier_enabled = False
    bp.enrollment_tier_stripe_item_id = None
    await db.commit()
    return {"enrollment_tier_disabled": True}


async def cancel_subscription(provider: User, db: AsyncSession) -> dict:
    """Cancel the provider's individual Stripe subscription immediately."""
    if not provider.stripe_subscription_id:
        return {"cancelled": False, "reason": "no subscription"}
    _init()
    try:
        sub = await asyncio.to_thread(
            stripe.Subscription.cancel,
            provider.stripe_subscription_id,
        )
        provider.subscription_status = sub.status  # "canceled"
        provider.stripe_subscription_id = None
        await db.commit()
        return {"cancelled": True, "subscription_id": sub.id, "status": sub.status}
    except stripe.InvalidRequestError:
        # Subscription already cancelled or doesn't exist — clear stale reference
        provider.stripe_subscription_id = None
        provider.subscription_status = "canceled"
        await db.commit()
        return {"cancelled": True, "reason": "already_cancelled"}


async def process_escrow_deduction(
    provider: User,
    remittance_amount: Decimal,
    remittance_id: uuid.UUID,
    db: AsyncSession,
) -> dict | None:
    if provider.escrow_balance_remaining <= 0:
        return None
    if not provider.stripe_customer_id:
        return None
    if not _configured():
        return None

    _init()
    balance = provider.escrow_balance_remaining
    if remittance_amount >= DEFERRED_BALANCE:
        deduction = balance
    else:
        deduction = min(remittance_amount * Decimal("0.5"), balance)

    try:
        pi = await asyncio.to_thread(
            stripe.PaymentIntent.create,
            amount=int(deduction * 100),
            currency="usd",
            customer=provider.stripe_customer_id,
            off_session=True,
            confirm=True,
            description=f"DoulaShield escrow deduction — ${deduction:.2f} of ${balance:.2f} remaining",
            metadata={
                "user_id": str(provider.id),
                "remittance_id": str(remittance_id),
                "type": "escrow_deduction",
            },
        )
    except stripe.CardError:
        return None

    new_balance = balance - deduction
    db.add(
        EscrowDeduction(
            id=uuid.uuid4(),
            provider_id=provider.id,
            remittance_id=remittance_id,
            amount_deducted=deduction,
            balance_before=balance,
            balance_after=new_balance,
            stripe_charge_id=pi.id,
        )
    )
    provider.escrow_balance_remaining = new_balance
    await db.commit()
    return {"amount_deducted": float(deduction), "balance_after": float(new_balance)}


async def transfer_to_partner(amount_cents: int, metadata: dict) -> dict | None:
    """Transfers STRIPE_PARTNER_SHARE of amount_cents to the configured partner account.
    Returns transfer details or None if partner account not configured or amount is zero."""
    if not settings.STRIPE_PARTNER_ACCOUNT_ID or amount_cents <= 0:
        return None
    partner_amount = int(amount_cents * settings.STRIPE_PARTNER_SHARE)
    if partner_amount <= 0:
        return None
    _init()
    transfer = await asyncio.to_thread(
        stripe.Transfer.create,
        amount=partner_amount,
        currency="usd",
        destination=settings.STRIPE_PARTNER_ACCOUNT_ID,
        metadata=metadata,
    )
    return {"transfer_id": transfer.id, "amount": partner_amount}

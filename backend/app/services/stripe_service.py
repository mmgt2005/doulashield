from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal

import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
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

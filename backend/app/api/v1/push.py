"""Browser push notification subscription endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.dependencies import CurrentUser, get_db
from app.models.push_subscription import PushSubscription
from app.schemas.push import PushSubscribeRequest, PushUnsubscribeRequest, VapidPublicKeyResponse

router = APIRouter(prefix="/push", tags=["push"])


@router.get("/vapid-public-key", response_model=VapidPublicKeyResponse)
async def get_vapid_public_key() -> VapidPublicKeyResponse:
    key = settings.VAPID_PUBLIC_KEY or None
    return VapidPublicKeyResponse(vapid_public_key=key)


@router.post("/subscribe")
async def subscribe(
    body: PushSubscribeRequest,
    request: Request,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Response:
    existing = await db.execute(
        select(PushSubscription).where(
            PushSubscription.user_id == current_user.id,
            PushSubscription.endpoint == body.endpoint,
        )
    )
    if not existing.scalar_one_or_none():
        sub = PushSubscription(
            user_id=current_user.id,
            endpoint=body.endpoint,
            p256dh_key=body.p256dh_key,
            auth_key=body.auth_key,
            user_agent=request.headers.get("user-agent"),
        )
        db.add(sub)
        await db.commit()
    return Response(status_code=204)


@router.delete("/unsubscribe")
async def unsubscribe(
    body: PushUnsubscribeRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Response:
    await db.execute(
        delete(PushSubscription).where(
            PushSubscription.user_id == current_user.id,
            PushSubscription.endpoint == body.endpoint,
        )
    )
    await db.commit()
    return Response(status_code=204)

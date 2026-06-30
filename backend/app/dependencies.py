from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Annotated

from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.audit import AuditLogger
from app.core.config import settings
from app.core.security import decode_token
from supabase._async.client import AsyncClient, create_client

if TYPE_CHECKING:
    from app.models.billing_provider import BillingProvider

# ── Database ──────────────────────────────────────────────────────────────────

_engine = create_async_engine(settings.DATABASE_URL, echo=False)
_AsyncSession = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore[call-overload]


async def get_db() -> AsyncSession:  # type: ignore[return]
    async with _AsyncSession() as session:
        yield session


# ── Supabase client (service role — server-side only) ────────────────────────

async def get_supabase() -> AsyncClient:  # type: ignore[return]
    client = await create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    yield client


# ── Audit logger ──────────────────────────────────────────────────────────────

async def get_audit(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuditLogger:
    return AuditLogger(db)


# ── Auth ──────────────────────────────────────────────────────────────────────

_bearer = HTTPBearer(auto_error=False)

_UNAUTH = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
_FORBIDDEN = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


class CurrentUser:
    def __init__(self, id: uuid.UUID, role: str) -> None:
        self.id = id
        self.role = role


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> CurrentUser:
    if not credentials:
        raise _UNAUTH
    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise _UNAUTH

    return CurrentUser(id=uuid.UUID(payload["sub"]), role=payload["role"])


async def require_admin(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
    if user.role != "admin":
        raise _FORBIDDEN
    return user


async def require_billing_admin(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
    if user.role not in ("admin", "billing_admin"):
        raise _FORBIDDEN
    return user


async def get_managed_billing_provider(
    user: Annotated[CurrentUser, Depends(require_billing_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> "BillingProvider":
    """Return the BillingProvider managed by the current billing_admin user."""
    from sqlalchemy.future import select
    from app.models.user import User as _User
    from app.models.billing_provider import BillingProvider as _BP

    row = await db.execute(select(_User.managed_billing_provider_id).where(_User.id == user.id))
    bp_id = row.scalar_one_or_none()
    if not bp_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No billing agency assigned to this account")
    bp_result = await db.execute(select(_BP).where(_BP.id == bp_id))
    bp = bp_result.scalar_one_or_none()
    if not bp:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Billing agency not found")
    return bp


async def require_billing_enrollment_tier(
    bp: Annotated["BillingProvider", Depends(get_managed_billing_provider)],
) -> "BillingProvider":
    """Gate access to enrollment features; requires enrollment_tier_enabled on the agency."""
    if not bp.enrollment_tier_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Enrollment tier is not enabled for your agency. Contact DoulaShield to enable it.",
        )
    return bp


def get_client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else None


def get_user_agent(request: Request) -> str:
    return request.headers.get("User-Agent", "")

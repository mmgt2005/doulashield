from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.dependencies import (
    CurrentUser,
    get_audit,
    get_client_ip,
    get_current_user,
    get_db,
    get_user_agent,
)
from app.core.audit import AuditLogger
from app.models.user import User
from app.schemas.admin import ProviderSettingsRead, ProviderSettingsUpdate, UserRead
from app.schemas.auth import (
    LoginRequest,
    MFASetupResponse,
    MFAVerifyRequest,
    RefreshResponse,
    TokenResponse,
)
from app.services.auth_service import AuthService
from app.services.eligibility_service import EligibilityService

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

_REFRESH_COOKIE = "ds_refresh"
_COOKIE_OPTS: dict = {
    "key": _REFRESH_COOKIE,
    "httponly": True,
    "secure": True,
    "samesite": "strict",
    "max_age": settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    "path": "/api/v1/auth",
}


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> TokenResponse:
    svc = AuthService(db, audit)
    try:
        token_resp, raw_refresh = await svc.login(
            body,
            ip=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if raw_refresh:
        response.set_cookie(**_COOKIE_OPTS, value=raw_refresh)
    return token_resp


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    ds_refresh: str | None = Cookie(default=None),
) -> RefreshResponse:
    if not ds_refresh:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")

    svc = AuthService(db, audit)
    try:
        access_token = await svc.refresh(
            ds_refresh,
            ip=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    return RefreshResponse(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
    ds_refresh: str | None = Cookie(default=None),
) -> None:
    if ds_refresh:
        svc = AuthService(db, audit)
        await svc.logout(ds_refresh)
    response.delete_cookie(_REFRESH_COOKIE, path="/api/v1/auth")


@router.get("/mfa/setup", response_model=MFASetupResponse)
async def mfa_setup(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> MFASetupResponse:
    svc = AuthService(db, audit)
    uri = await svc.setup_mfa(current_user.id)
    return MFASetupResponse(provisioning_uri=uri)


@router.get("/me", response_model=UserRead)
async def get_me(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserRead:
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserRead.model_validate(user)


@router.get("/me/provider-settings", response_model=ProviderSettingsRead)
async def get_provider_settings(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> ProviderSettingsRead:
    try:
        return await EligibilityService(db, audit).get_provider_settings(current_user.id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.patch("/me/provider-settings", response_model=ProviderSettingsRead)
async def update_provider_settings(
    request: Request,
    body: ProviderSettingsUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> ProviderSettingsRead:
    try:
        return await EligibilityService(db, audit).update_provider_settings(
            current_user.id, body, get_client_ip(request), get_user_agent(request)
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/mfa/verify", status_code=status.HTTP_204_NO_CONTENT)
async def mfa_verify(
    request: Request,
    body: MFAVerifyRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> None:
    svc = AuthService(db, audit)
    try:
        await svc.verify_mfa(
            current_user.id,
            body.totp_code,
            ip=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code")

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
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
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.schemas.admin import ProviderSettingsRead, ProviderSettingsUpdate, UserRead
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    MFASetupResponse,
    MFAVerifyRequest,
    RefreshResponse,
    TokenResponse,
)
from app.services import email_service
from app.services.auth_service import AuthService
from app.services.eligibility_service import EligibilityService
from app.core.security import decode_token, hash_password, is_valid_password, verify_password
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

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


@router.post("/me/provider-signature")
async def save_provider_signature(
    request: Request,
    body: dict,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> dict:
    """Upload provider signature image and save the storage path."""
    import base64
    import datetime as dt
    from app.services import ocr_service as _ocr

    data_url: str = body.get("signature_data_url", "")
    if not data_url.startswith("data:image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image data.")

    try:
        header, b64 = data_url.split(",", 1)
        image_bytes = base64.b64decode(b64)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not decode image.")

    content_type = "image/png"
    try:
        path = await _ocr.store_image(image_bytes, content_type, None, current_user.id, "provider-signature")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Storage failed: {exc}")

    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.provider_signature_path = path
    await db.commit()

    await audit.log(
        action="SAVE_PROVIDER_SIGNATURE",
        resource_type="user",
        resource_id=current_user.id,
        user_id=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    return {"path": path}


@router.post("/me/change-password")
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> dict:
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not verify_password(body.current_password, user.password_hash):  # type: ignore[arg-type]
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    if not is_valid_password(body.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 12 characters and include uppercase, lowercase, digit, and special character.",
        )

    user.password_hash = hash_password(body.new_password)  # type: ignore[assignment]
    await db.commit()

    await audit.log(
        action="CHANGE_PASSWORD",
        resource_type="user",
        resource_id=current_user.id,
        user_id=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    return {"message": "Password updated"}


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


_RESET_RESPONSE = {"message": "If that email address is registered, a reset link has been sent."}
_RESET_EXPIRY_HOURS = 1


@router.post("/forgot-password")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> dict:
    result = await db.execute(select(User).where(User.email == body.email.strip().lower()))
    user = result.scalar_one_or_none()

    if user and user.is_active:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=_RESET_EXPIRY_HOURS)
        db.add(PasswordResetToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        ))
        await db.commit()

        reset_url = f"{settings.FRONTEND_ORIGIN}/reset-password?token={raw_token}"
        try:
            await email_service.send_password_reset_email(
                email=user.email,
                name=user.full_name or user.email,
                reset_url=reset_url,
            )
        except Exception:
            pass  # don't reveal email-send failures to the caller

        await audit.log(
            action="REQUEST_PASSWORD_RESET",
            resource_type="user",
            resource_id=user.id,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )

    return _RESET_RESPONSE


_bearer = HTTPBearer()


@router.post("/impersonate/end", status_code=status.HTTP_204_NO_CONTENT)
async def end_impersonation(
    request: Request,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> None:
    try:
        payload = decode_token(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")

    imp_claim = payload.get("imp")
    if not imp_claim:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not an impersonation session")

    await audit.log(
        action="IMPERSONATE_END",
        resource_type="user",
        resource_id=current_user.id,
        user_id=uuid.UUID(imp_claim),
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        extra_context={
            "admin_id": imp_claim,
            "target_id": str(current_user.id),
        },
    )


@router.post("/reset-password")
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> dict:
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
    )
    reset_token = result.scalar_one_or_none()
    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset link is invalid or has expired.",
        )

    if not is_valid_password(body.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 12 characters and include uppercase, lowercase, digit, and special character.",
        )

    user_result = await db.execute(select(User).where(User.id == reset_token.user_id))
    user = user_result.scalar_one()
    user.password_hash = hash_password(body.new_password)  # type: ignore[assignment]
    reset_token.used_at = now
    await db.commit()

    await audit.log(
        action="RESET_PASSWORD",
        resource_type="user",
        resource_id=user.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    return {"message": "Password updated. You can now log in."}

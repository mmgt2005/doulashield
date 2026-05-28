from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import pyotp
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import AuditLogger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    is_valid_password,
    verify_password,
)
from app.core.config import settings
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class AuthService:
    def __init__(self, db: AsyncSession, audit: AuditLogger) -> None:
        self._db = db
        self._audit = audit

    async def login(
        self, request: LoginRequest, ip: str, user_agent: str
    ) -> tuple[TokenResponse, str]:
        """Returns (TokenResponse, raw_refresh_token). Raises ValueError on failure."""
        result = await self._db.execute(select(User).where(User.email == request.email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(request.password, user.password_hash):  # type: ignore[attr-defined]
            await self._audit.log(
                action="LOGIN_FAIL",
                ip_address=ip,
                user_agent=user_agent,
                extra_context={"email_domain": request.email.split("@")[-1]},
            )
            raise ValueError("Invalid credentials")

        if not user.is_active:
            raise ValueError("Account is deactivated")

        if user.mfa_enabled:
            if not request.totp_code:
                return TokenResponse(mfa_required=True, access_token=""), ""
            totp = pyotp.TOTP(user.totp_secret)  # type: ignore[attr-defined]
            if not totp.verify(request.totp_code, valid_window=1):
                await self._audit.log(
                    action="MFA_FAIL",
                    ip_address=ip,
                    user_agent=user_agent,
                    user_id=user.id,
                )
                raise ValueError("Invalid MFA code")

        access_token = create_access_token(str(user.id), user.role)
        raw_refresh = create_refresh_token(str(user.id))

        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        self._db.add(
            RefreshToken(
                user_id=user.id,
                token_hash=_hash_token(raw_refresh),
                expires_at=expires_at,
            )
        )
        await self._db.commit()

        await self._audit.log(
            action="LOGIN",
            ip_address=ip,
            user_agent=user_agent,
            user_id=user.id,
        )
        return TokenResponse(access_token=access_token), raw_refresh

    async def refresh(self, raw_refresh: str, ip: str, user_agent: str) -> str:
        """Returns a new access token. Raises ValueError if token is invalid/revoked."""
        try:
            payload = decode_token(raw_refresh)
        except JWTError:
            raise ValueError("Invalid refresh token")

        if payload.get("type") != "refresh":
            raise ValueError("Not a refresh token")

        token_hash = _hash_token(raw_refresh)
        result = await self._db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        record = result.scalar_one_or_none()

        if not record or record.revoked or record.expires_at < datetime.now(timezone.utc):
            raise ValueError("Refresh token expired or revoked")

        user_result = await self._db.execute(select(User).where(User.id == record.user_id))
        user = user_result.scalar_one_or_none()
        if not user or not user.is_active:
            raise ValueError("User not found or inactive")

        return create_access_token(str(user.id), user.role)

    async def logout(self, raw_refresh: str) -> None:
        token_hash = _hash_token(raw_refresh)
        result = await self._db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        record = result.scalar_one_or_none()
        if record:
            record.revoked = True
            await self._db.commit()

    async def setup_mfa(self, user_id: uuid.UUID) -> str:
        """Returns the TOTP provisioning URI."""
        result = await self._db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        secret = pyotp.random_base32()
        user.totp_secret = secret  # type: ignore[attr-defined]
        await self._db.commit()
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=user.email, issuer_name="DoulaShield")

    async def verify_mfa(self, user_id: uuid.UUID, code: str, ip: str, user_agent: str) -> None:
        result = await self._db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        totp = pyotp.TOTP(user.totp_secret)  # type: ignore[attr-defined]
        if not totp.verify(code, valid_window=1):
            raise ValueError("Invalid TOTP code")
        user.mfa_enabled = True
        await self._db.commit()
        await self._audit.log(
            action="MFA_ENROLL",
            ip_address=ip,
            user_agent=user_agent,
            user_id=user_id,
        )

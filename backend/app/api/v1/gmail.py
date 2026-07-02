import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.encryption import decrypt_field, encrypt_field
from app.dependencies import CurrentUser, get_db, require_admin
from app.models.user import User

log = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/gmail", tags=["admin"])

_REDIRECT_URI = lambda: f"{settings.BACKEND_URL}/api/v1/admin/gmail/callback"
_STATE_ALGO = "HS256"
_STATE_TTL = 600  # seconds


def _require_configured():
    from app.services import gmail_service
    if not gmail_service._configured():
        raise HTTPException(
            status_code=503,
            detail="Gmail OAuth is not configured (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET missing)",
        )


def _make_state(user_id: uuid.UUID) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(seconds=_STATE_TTL),
        "iss": "doulashield-gmail",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=_STATE_ALGO)


def _decode_state(state: str) -> uuid.UUID:
    try:
        payload = jwt.decode(
            state,
            settings.JWT_SECRET_KEY,
            algorithms=[_STATE_ALGO],
            options={"require": ["sub", "exp", "iss"]},
        )
        if payload.get("iss") != "doulashield-gmail":
            raise ValueError("wrong issuer")
        return uuid.UUID(payload["sub"])
    except (JWTError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state") from exc


@router.get("/status")
async def gmail_status(
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> dict:
    return {
        "connected": current_user.gmail_connected_email is not None,
        "email": current_user.gmail_connected_email,
    }


@router.get("/auth-url")
async def gmail_auth_url(
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> dict:
    """Return the Google OAuth consent URL. Frontend fetches this via axios, then navigates."""
    _require_configured()
    from app.services import gmail_service

    state = _make_state(current_user.id)
    flow = gmail_service.get_oauth_flow(_REDIRECT_URI())
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=state,
    )
    return {"auth_url": auth_url}


@router.get("/callback")
async def gmail_callback(
    db: Annotated[AsyncSession, Depends(get_db)],
    code: str = Query(...),
    state: str = Query(...),
) -> RedirectResponse:
    """Google redirects here after consent. No Bearer token — user identity comes from state."""
    _require_configured()

    user_id = _decode_state(state)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    from app.services import gmail_service
    tokens = await gmail_service.exchange_code(code, _REDIRECT_URI())

    user.gmail_access_token_encrypted = encrypt_field(tokens["access_token"])
    if tokens.get("refresh_token"):
        user.gmail_refresh_token_encrypted = encrypt_field(tokens["refresh_token"])
    if tokens.get("expiry"):
        expiry = tokens["expiry"]
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        user.gmail_token_expiry = expiry

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials(
            token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        profile = service.users().getProfile(userId="me").execute()
        user.gmail_connected_email = profile.get("emailAddress")
    except Exception:
        log.warning("Could not fetch Gmail profile after OAuth", exc_info=True)
        user.gmail_connected_email = "connected"

    await db.commit()
    return RedirectResponse(url=f"{settings.FRONTEND_ORIGIN}/admin/gmail?connected=1")


@router.delete("/disconnect")
async def gmail_disconnect(
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    if current_user.gmail_access_token_encrypted:
        try:
            import httpx
            token = decrypt_field(current_user.gmail_access_token_encrypted)
            async with httpx.AsyncClient() as client:
                await client.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": token},
                )
        except Exception:
            log.debug("Could not revoke Gmail token", exc_info=True)

    current_user.gmail_access_token_encrypted = None
    current_user.gmail_refresh_token_encrypted = None
    current_user.gmail_token_expiry = None
    current_user.gmail_connected_email = None
    await db.commit()
    return {"disconnected": True}


@router.get("/inbox")
async def gmail_inbox(
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    q: str | None = Query(None),
) -> list[dict]:
    if not current_user.gmail_connected_email:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    from app.services import gmail_service
    return await gmail_service.fetch_inbox(current_user, db, q=q)


@router.get("/messages")
async def gmail_messages_for_lead(
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    email: str = Query(...),
) -> list[dict]:
    if not current_user.gmail_connected_email:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    from app.services import gmail_service
    return await gmail_service.fetch_messages_for_lead(current_user, db, email)


@router.get("/messages/{message_id}")
async def gmail_message_detail(
    message_id: str,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    if not current_user.gmail_connected_email:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    from app.services import gmail_service
    return await gmail_service.fetch_message_detail(current_user, db, message_id)

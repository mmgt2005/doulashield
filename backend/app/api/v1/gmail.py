import base64
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import RedirectResponse, Response
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.encryption import encrypt_field, decrypt_field
from app.dependencies import CurrentUser, get_db, require_admin
from app.models.user import User

log = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/gmail", tags=["admin"])

_REDIRECT_URI = lambda: f"{settings.BACKEND_URL}/api/v1/admin/gmail/callback"
_STATE_ALGO = "HS256"
_STATE_TTL = 600


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


async def _get_shared_gmail_user(db: AsyncSession) -> User | None:
    """Return the first admin that has Gmail tokens stored (shared account)."""
    result = await db.execute(
        select(User)
        .where(User.role == "admin")
        .where(User.gmail_connected_email.isnot(None))
        .limit(1)
    )
    return result.scalar_one_or_none()


@router.get("/status")
async def gmail_status(
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Shared status — connected if any admin has Gmail tokens stored."""
    gmail_user = await _get_shared_gmail_user(db)
    return {
        "connected": gmail_user is not None,
        "email": gmail_user.gmail_connected_email if gmail_user else None,
    }


@router.get("/auth-url")
async def gmail_auth_url(
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> dict:
    _require_configured()
    from app.services import gmail_service

    state = _make_state(current_user.id)
    auth_url = gmail_service.build_authorization_url(_REDIRECT_URI(), state)
    return {"auth_url": auth_url}


@router.get("/callback")
async def gmail_callback(
    db: Annotated[AsyncSession, Depends(get_db)],
    code: str = Query(...),
    state: str = Query(...),
) -> RedirectResponse:
    """Google redirects here. Identity comes from signed state JWT — no Bearer token needed."""
    _require_configured()

    user_id = _decode_state(state)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    from app.services import gmail_service

    try:
        tokens = await gmail_service.exchange_code(code, _REDIRECT_URI())
    except Exception as exc:
        log.error("Gmail token exchange failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=f"Google token exchange failed: {exc}") from exc

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
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Clear Gmail tokens from all admins (shared account disconnect)."""
    result = await db.execute(
        select(User)
        .where(User.role == "admin")
        .where(User.gmail_connected_email.isnot(None))
    )
    gmail_users = result.scalars().all()

    for u in gmail_users:
        if u.gmail_access_token_encrypted:
            try:
                import httpx
                token = decrypt_field(u.gmail_access_token_encrypted)
                async with httpx.AsyncClient() as client:
                    await client.post("https://oauth2.googleapis.com/revoke", params={"token": token})
            except Exception:
                log.debug("Could not revoke Gmail token for user %s", u.id, exc_info=True)
        u.gmail_access_token_encrypted = None
        u.gmail_refresh_token_encrypted = None
        u.gmail_token_expiry = None
        u.gmail_connected_email = None

    await db.commit()
    return {"disconnected": True}


@router.get("/inbox")
async def gmail_inbox(
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    q: str | None = Query(None),
) -> list[dict]:
    gmail_user = await _get_shared_gmail_user(db)
    if not gmail_user:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    from app.services import gmail_service
    return await gmail_service.fetch_inbox(gmail_user, db, q=q)


@router.get("/messages")
async def gmail_messages_for_lead(
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    email: str = Query(...),
) -> list[dict]:
    gmail_user = await _get_shared_gmail_user(db)
    if not gmail_user:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    from app.services import gmail_service
    return await gmail_service.fetch_messages_for_lead(gmail_user, db, email)


@router.get("/messages/{message_id}")
async def gmail_message_detail(
    message_id: str,
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    gmail_user = await _get_shared_gmail_user(db)
    if not gmail_user:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    from app.services import gmail_service
    return await gmail_service.fetch_message_detail(gmail_user, db, message_id)


@router.post("/send")
async def gmail_send(
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    to: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...),
    files: list[UploadFile] = File(default=[]),
) -> dict:
    gmail_user = await _get_shared_gmail_user(db)
    if not gmail_user:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    from app.services import gmail_service

    attachment_data = [
        (f.filename or "attachment", await f.read(), f.content_type or "application/octet-stream")
        for f in files
    ]
    result = await gmail_service.send_message(
        gmail_user, db, to, subject, body, attachments=attachment_data or None
    )
    return {"sent": True, **result}


@router.post("/messages/{message_id}/reply")
async def gmail_reply(
    message_id: str,
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    to: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...),
    files: list[UploadFile] = File(default=[]),
) -> dict:
    gmail_user = await _get_shared_gmail_user(db)
    if not gmail_user:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    from app.services import gmail_service

    orig = await gmail_service.fetch_message_reply_headers(gmail_user, db, message_id)
    attachment_data = [
        (f.filename or "attachment", await f.read(), f.content_type or "application/octet-stream")
        for f in files
    ]
    result = await gmail_service.send_message(
        gmail_user,
        db,
        to,
        subject,
        body,
        attachments=attachment_data or None,
        in_reply_to=orig["message_id"] or None,
        references=orig["references"] or None,
    )
    return {"sent": True, **result}


@router.get("/messages/{message_id}/attachments/{attachment_id}")
async def gmail_attachment(
    message_id: str,
    attachment_id: str,
    filename: str = Query("attachment"),
    mime_type: str = Query("application/octet-stream"),
    _: Annotated[CurrentUser, Depends(require_admin)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> Response:
    gmail_user = await _get_shared_gmail_user(db)
    if not gmail_user:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    from app.services import gmail_service
    att = await gmail_service.fetch_attachment(gmail_user, db, message_id, attachment_id)
    raw = att.get("data", "")
    data = base64.urlsafe_b64decode(raw + "==") if raw else b""
    safe_name = filename.replace('"', "")
    return Response(
        content=data,
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )

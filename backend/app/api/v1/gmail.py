import logging
from datetime import timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.encryption import decrypt_field, encrypt_field
from app.dependencies import CurrentUser, get_db, require_admin

log = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/gmail", tags=["admin"])


def _redirect_uri(request: Request) -> str:
    return f"{settings.BACKEND_URL}/api/v1/admin/gmail/callback"


def _require_configured():
    from app.services import gmail_service
    if not gmail_service._configured():
        raise HTTPException(status_code=503, detail="Gmail OAuth is not configured (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET missing)")


@router.get("/status")
async def gmail_status(
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> dict:
    return {
        "connected": current_user.gmail_connected_email is not None,
        "email": current_user.gmail_connected_email,
    }


@router.get("/connect")
async def gmail_connect(
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> RedirectResponse:
    _require_configured()
    from app.services import gmail_service
    redirect_uri = _redirect_uri(request)
    auth_url, state = gmail_service.get_authorization_url(redirect_uri)
    response = RedirectResponse(url=auth_url)
    response.set_cookie("gmail_oauth_state", state, httponly=True, samesite="lax", max_age=600)
    return response


@router.get("/callback")
async def gmail_callback(
    request: Request,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    code: str = Query(...),
    state: str = Query(...),
) -> RedirectResponse:
    _require_configured()

    stored_state = request.cookies.get("gmail_oauth_state")
    if stored_state and stored_state != state:
        raise HTTPException(status_code=400, detail="OAuth state mismatch")

    from app.services import gmail_service
    redirect_uri = _redirect_uri(request)
    tokens = await gmail_service.exchange_code(code, redirect_uri)

    current_user.gmail_access_token_encrypted = encrypt_field(tokens["access_token"])
    if tokens.get("refresh_token"):
        current_user.gmail_refresh_token_encrypted = encrypt_field(tokens["refresh_token"])
    if tokens.get("expiry"):
        expiry = tokens["expiry"]
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        current_user.gmail_token_expiry = expiry

    # Fetch the connected email address
    try:
        from google.auth.transport.requests import Request as GRequest
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
        current_user.gmail_connected_email = profile.get("emailAddress")
    except Exception:
        log.warning("Could not fetch Gmail profile after OAuth", exc_info=True)
        current_user.gmail_connected_email = "connected"

    await db.commit()

    response = RedirectResponse(url=f"{settings.FRONTEND_ORIGIN}/admin/gmail?connected=1")
    response.delete_cookie("gmail_oauth_state")
    return response


@router.delete("/disconnect")
async def gmail_disconnect(
    current_user: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    # Optionally revoke token at Google
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

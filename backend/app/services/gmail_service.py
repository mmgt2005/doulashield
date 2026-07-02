import asyncio
import base64
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.encryption import decrypt_field, encrypt_field

log = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def _configured() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def get_oauth_flow(redirect_uri: str):
    from google_auth_oauthlib.flow import Flow

    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=_SCOPES, redirect_uri=redirect_uri)
    return flow


def get_authorization_url(redirect_uri: str) -> tuple[str, str]:
    flow = get_oauth_flow(redirect_uri)
    url, state = flow.authorization_url(access_type="offline", prompt="consent")
    return url, state


async def exchange_code(code: str, redirect_uri: str) -> dict:
    """Exchange auth code for tokens directly — bypasses google_auth_oauthlib Flow
    so no PKCE code_verifier is required (avoids 'Missing code verifier' error)."""
    import httpx
    from datetime import timedelta

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    expiry = None
    if "expires_in" in data:
        expiry = datetime.now(timezone.utc) + timedelta(seconds=int(data["expires_in"]))

    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token"),
        "expiry": expiry,
    }


async def _get_credentials(user):
    from google.oauth2.credentials import Credentials

    access_token = decrypt_field(user.gmail_access_token_encrypted) if user.gmail_access_token_encrypted else None
    refresh_token = decrypt_field(user.gmail_refresh_token_encrypted) if user.gmail_refresh_token_encrypted else None

    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=_SCOPES,
    )
    if user.gmail_token_expiry:
        creds.expiry = user.gmail_token_expiry.replace(tzinfo=None)

    return creds


async def _build_service(user, db: AsyncSession):
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = await _get_credentials(user)

    if creds.expired and creds.refresh_token:
        await asyncio.to_thread(creds.refresh, Request())
        user.gmail_access_token_encrypted = encrypt_field(creds.token)
        user.gmail_token_expiry = creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else None
        await db.commit()

    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    return service


def _extract_headers(headers: list[dict], names: set[str]) -> dict[str, str]:
    result = {}
    for h in headers:
        if h.get("name", "").lower() in names:
            result[h["name"].lower()] = h.get("value", "")
    return result


def _parse_message_summary(msg: dict) -> dict:
    payload = msg.get("payload", {})
    headers = payload.get("headers", [])
    h = _extract_headers(headers, {"subject", "from", "to", "date"})
    label_ids = msg.get("labelIds", [])
    return {
        "id": msg.get("id"),
        "subject": h.get("subject", "(no subject)"),
        "from": h.get("from", ""),
        "to": h.get("to", ""),
        "date": h.get("date", ""),
        "snippet": msg.get("snippet", ""),
        "unread": "UNREAD" in label_ids,
    }


def _decode_body(payload: dict) -> str:
    parts = payload.get("parts", [])
    if parts:
        for part in parts:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        for part in parts:
            if part.get("mimeType") == "text/html":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
    data = payload.get("body", {}).get("data", "")
    if data:
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
    return ""


async def fetch_inbox(user, db: AsyncSession, max_results: int = 30, q: str | None = None) -> list[dict]:
    service = await _build_service(user, db)

    def _list():
        kwargs = {"userId": "me", "labelIds": ["INBOX"], "maxResults": max_results}
        if q:
            kwargs["q"] = q
        return service.users().messages().list(**kwargs).execute()

    result = await asyncio.to_thread(_list)
    messages = result.get("messages", [])

    summaries = []
    for m in messages:
        try:
            msg = await asyncio.to_thread(
                lambda mid=m["id"]: service.users().messages().get(userId="me", id=mid, format="metadata",
                    metadataHeaders=["Subject", "From", "To", "Date"]).execute()
            )
            summaries.append(_parse_message_summary(msg))
        except Exception:
            log.debug("Failed to fetch gmail message %s", m["id"], exc_info=True)

    return summaries


async def fetch_messages_for_lead(user, db: AsyncSession, lead_email: str, max_results: int = 10) -> list[dict]:
    service = await _build_service(user, db)
    query = f"from:{lead_email} OR to:{lead_email}"

    def _list():
        return service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()

    result = await asyncio.to_thread(_list)
    messages = result.get("messages", [])

    summaries = []
    for m in messages:
        try:
            msg = await asyncio.to_thread(
                lambda mid=m["id"]: service.users().messages().get(userId="me", id=mid, format="metadata",
                    metadataHeaders=["Subject", "From", "To", "Date"]).execute()
            )
            summaries.append(_parse_message_summary(msg))
        except Exception:
            log.debug("Failed to fetch gmail message %s", m["id"], exc_info=True)

    return summaries


async def fetch_message_detail(user, db: AsyncSession, message_id: str) -> dict:
    service = await _build_service(user, db)

    msg = await asyncio.to_thread(
        lambda: service.users().messages().get(userId="me", id=message_id, format="full").execute()
    )
    payload = msg.get("payload", {})
    headers = payload.get("headers", [])
    h = _extract_headers(headers, {"subject", "from", "to", "date", "cc", "bcc"})
    label_ids = msg.get("labelIds", [])
    body = _decode_body(payload)

    return {
        "id": msg.get("id"),
        "subject": h.get("subject", "(no subject)"),
        "from": h.get("from", ""),
        "to": h.get("to", ""),
        "cc": h.get("cc", ""),
        "date": h.get("date", ""),
        "snippet": msg.get("snippet", ""),
        "unread": "UNREAD" in label_ids,
        "body": body,
    }

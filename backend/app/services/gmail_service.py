import asyncio
import base64
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.encryption import decrypt_field, encrypt_field

log = logging.getLogger(__name__)

_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


def _configured() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def build_authorization_url(redirect_uri: str, state: str) -> str:
    """Build OAuth consent URL manually — no PKCE, no code_challenge."""
    import urllib.parse

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)


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
        if not resp.is_success:
            raise ValueError(f"Google token endpoint {resp.status_code}: {resp.text}")
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


class GmailTokenExpired(Exception):
    """Raised when the stored Gmail OAuth token is expired and cannot be refreshed."""


async def _build_service(user, db: AsyncSession):
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = await _get_credentials(user)

    if creds.expired:
        if not creds.refresh_token:
            raise GmailTokenExpired("No refresh token stored")
        try:
            await asyncio.to_thread(creds.refresh, Request())
            user.gmail_access_token_encrypted = encrypt_field(creds.token)
            user.gmail_token_expiry = creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else None
            await db.commit()
        except GmailTokenExpired:
            raise
        except Exception as exc:
            # Token revoked or refresh failed — clear stored tokens so /status returns disconnected
            user.gmail_access_token_encrypted = None
            user.gmail_refresh_token_encrypted = None
            user.gmail_token_expiry = None
            user.gmail_connected_email = None
            await db.commit()
            log.warning("Gmail token refresh failed, cleared stored tokens: %s", exc)
            raise GmailTokenExpired("Token refresh failed") from exc

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


def _extract_attachments(payload: dict) -> list[dict]:
    """Walk the MIME tree and return metadata for every part with a filename."""
    attachments: list[dict] = []

    def _walk(part: dict) -> None:
        filename = part.get("filename", "")
        if filename:
            body = part.get("body", {})
            attachments.append({
                "id": body.get("attachmentId"),
                "filename": filename,
                "mimeType": part.get("mimeType", "application/octet-stream"),
                "size": body.get("size", 0),
            })
        for subpart in part.get("parts", []):
            _walk(subpart)

    _walk(payload)
    return attachments


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


async def fetch_inbox(user, db: AsyncSession, max_results: int = 30, q: str | None = None, label: str = "INBOX") -> list[dict]:
    service = await _build_service(user, db)

    def _list():
        kwargs = {"userId": "me", "labelIds": [label], "maxResults": max_results}
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
        "attachments": _extract_attachments(payload),
    }


def _text_to_html(text: str, logo_url: str | None = None) -> str:
    """Convert plain text to HTML with optional logo header."""
    import html as _html
    import re

    safe = _html.escape(text)
    safe = re.sub(r"(https?://\S+)", r'<a href="\1" style="color:#2563eb">\1</a>', safe)
    safe = safe.replace("\n", "<br>\n")

    logo_block = ""
    if logo_url:
        logo_block = (
            f'<div style="padding:16px 24px;background:#ffffff;border:1px solid #e5e7eb;border-bottom:none;border-radius:8px 8px 0 0">'
            f'<img src="{logo_url}" alt="DoulaShield" width="130" height="auto"'
            f' style="display:block;max-width:100%"/>'
            f'</div>'
        )
        radius = "0 0 8px 8px"
    else:
        radius = "8px"

    body_block = (
        f'<div style="font-family:sans-serif;font-size:14px;line-height:1.6;color:#374151;'
        f'padding:24px;background:#ffffff;border:1px solid #e5e7eb;'
        f'border-top:{"none" if logo_url else "1px solid #e5e7eb"};border-radius:{radius}">'
        f'{safe}'
        f'</div>'
    )

    return (
        f'<div style="max-width:600px;margin:0 auto">'
        f'{logo_block}{body_block}'
        f'</div>'
    )


async def fetch_message_reply_headers(user, db: AsyncSession, message_id: str) -> dict:
    """Fetch Message-ID, References, Subject, and From headers needed to construct a reply."""
    service = await _build_service(user, db)
    msg = await asyncio.to_thread(
        lambda: service.users().messages().get(
            userId="me",
            id=message_id,
            format="metadata",
            metadataHeaders=["Message-ID", "References", "Subject", "From"],
        ).execute()
    )
    payload = msg.get("payload", {})
    headers = payload.get("headers", [])
    h = _extract_headers(headers, {"message-id", "references", "subject", "from"})
    return {
        "message_id": h.get("message-id", ""),
        "references": h.get("references", ""),
        "subject": h.get("subject", ""),
        "from_": h.get("from", ""),
    }


async def send_message(
    user,
    db: AsyncSession,
    to: str,
    subject: str,
    body_text: str,
    attachments: list[tuple[str, bytes, str]] | None = None,
    in_reply_to: str | None = None,
    references: str | None = None,
) -> dict:
    """Build and send an email via the Gmail API.

    attachments: list of (filename, raw_bytes, content_type)
    in_reply_to / references: RFC 2822 threading headers for replies.
    """
    import email.encoders
    from email.generator import BytesGenerator
    from email.mime.base import MIMEBase
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from io import BytesIO

    from_addr = settings.GMAIL_SEND_AS or (user.gmail_connected_email or "me")

    logo_url = f"{settings.FRONTEND_ORIGIN}/logo.png" if settings.FRONTEND_ORIGIN else None

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(body_text, "plain", "utf-8"))
    alt.attach(MIMEText(_text_to_html(body_text, logo_url=logo_url), "html", "utf-8"))

    if attachments:
        outer: MIMEMultipart = MIMEMultipart("mixed")
        outer.attach(alt)
        for filename, data, content_type in attachments:
            main_type, _, sub_type = content_type.partition("/")
            safe_name = filename.replace('"', "")
            part = MIMEBase(main_type or "application", sub_type or "octet-stream", name=safe_name)
            part.set_payload(data)
            email.encoders.encode_base64(part)
            part.add_header("Content-Disposition", "attachment", filename=safe_name)
            outer.attach(part)
    else:
        outer = alt  # type: ignore[assignment]

    outer["From"] = from_addr
    outer["To"] = to
    outer["Subject"] = subject
    if in_reply_to:
        outer["In-Reply-To"] = in_reply_to
        refs = f"{references} {in_reply_to}".strip() if references else in_reply_to
        outer["References"] = refs

    buf = BytesIO()
    BytesGenerator(buf, mangle_from_=False).flatten(outer)
    raw = base64.urlsafe_b64encode(buf.getvalue()).decode()

    service = await _build_service(user, db)
    result = await asyncio.to_thread(
        lambda: service.users().messages().send(userId="me", body={"raw": raw}).execute()
    )
    return {"id": result.get("id"), "threadId": result.get("threadId")}


async def fetch_attachment(user, db: AsyncSession, message_id: str, attachment_id: str) -> dict:
    service = await _build_service(user, db)
    att = await asyncio.to_thread(
        lambda: service.users().messages().attachments().get(
            userId="me", messageId=message_id, id=attachment_id
        ).execute()
    )
    return {
        "data": att.get("data", ""),
        "size": att.get("size", 0),
    }

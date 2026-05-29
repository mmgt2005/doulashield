from __future__ import annotations

import base64
import logging
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import AuditLogger
from app.core.config import settings
from app.core.encryption import decrypt_field
from app.models.user import User
from app.models.visit import Visit
from app.services import ocr_service

logger = logging.getLogger(__name__)

MA91_TEXT = (
    "My signature certifies that I received a service or item on the date listed above. "
    "I understand that payment for this service will be from Federal and State funds, and that "
    "any false claims or concealment of material may be prosecuted under Federal and State laws."
)

ZIPZIGN_BASE = "https://api.zipzign.com/v1"


async def save_in_person_signature(
    image_data_url: str,
    visit_id: uuid.UUID,
    patient_id: uuid.UUID,
    patient_name: str,
    user_id: uuid.UUID,
    db: AsyncSession,
    audit: AuditLogger,
    ip: str,
    user_agent: str,
) -> dict:
    """Save a base64 canvas signature to Supabase Storage and mark the visit MA 91 as signed."""
    if not image_data_url.startswith("data:image/png;base64,"):
        raise ValueError("Invalid signature data — expected PNG data URL")

    raw_b64 = image_data_url.split(",", 1)[1]
    image_bytes = base64.b64decode(raw_b64)

    path = await ocr_service.store_image(
        image_bytes,
        "image/png",
        patient_id,
        user_id,
        f"ma91-{visit_id}",
    )

    now = datetime.now(timezone.utc)

    result = await db.execute(select(Visit).where(Visit.id == visit_id))
    visit = result.scalar_one_or_none()
    if not visit:
        raise ValueError("Visit not found")

    visit.ma91_signed_at = now
    visit.ma91_signature_path = path
    visit.ma91_signed_by_name = patient_name
    visit.ma91_status = "signed"
    await db.commit()

    await audit.log(
        action="SIGN_MA91_IN_PERSON",
        resource_type="visit",
        resource_id=visit_id,
        ip_address=ip,
        user_agent=user_agent,
        user_id=user_id,
        extra_context={"patient_name": patient_name},
    )

    return {"status": "signed", "signature_path": path, "signed_at": now.isoformat()}


async def request_telehealth_signature(
    provider_user_id: uuid.UUID,
    patient_name: str,
    patient_email: str,
    visit_date: str,
    visit_id: uuid.UUID,
    patient_id: uuid.UUID,
    db: AsyncSession,
    audit: AuditLogger,
    ip: str,
    user_agent: str,
) -> dict:
    """Send a ZipZign e-signature request for the MA 91 form to the patient's email."""
    user_result = await db.execute(select(User).where(User.id == provider_user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise ValueError("User not found")
    if not user.contact_email:
        raise ValueError("Provider email not configured — add your contact email in Settings")

    admin_result = await db.execute(
        select(User)
        .where(User.role == "admin", User.zipzign_api_key_encrypted.isnot(None))
        .limit(1)
    )
    admin = admin_result.scalar_one_or_none()
    if not admin:
        raise ValueError("ZipZign not configured — an admin must add the API key in Settings")

    api_key = decrypt_field(admin.zipzign_api_key_encrypted)
    provider_name = user.full_name or user.email

    html_document = _build_ma91_html(
        provider_name=provider_name,
        provider_npi=user.npi or "N/A",
        patient_name=patient_name,
        visit_date=visit_date,
    )

    webhook_url = f"{settings.BACKEND_URL}/api/v1/signatures/webhook"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{ZIPZIGN_BASE}/requests",
            json={
                "document": {
                    "html": html_document,
                    "title": "MA 91 Encounter Form Certification",
                },
                "signers": [
                    {
                        "name": patient_name,
                        "email": patient_email,
                        "role": "patient",
                    }
                ],
                "sender": {
                    "name": provider_name,
                    "email": user.contact_email,
                },
                "webhook_url": webhook_url,
                "metadata": {"visit_id": str(visit_id)},
            },
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    if resp.status_code not in (200, 201):
        logger.error("ZipZign API error %s: %s", resp.status_code, resp.text)
        raise ValueError("Failed to send signature request — check your ZipZign API key")

    data = resp.json()
    request_id = data.get("id") or data.get("request_id") or str(data)

    result = await db.execute(select(Visit).where(Visit.id == visit_id))
    visit = result.scalar_one_or_none()
    if not visit:
        raise ValueError("Visit not found")

    visit.ma91_zipzign_request_id = str(request_id)
    visit.ma91_status = "pending"
    visit.ma91_signed_by_name = patient_name
    await db.commit()

    await audit.log(
        action="REQUEST_TELEHEALTH_MA91",
        resource_type="visit",
        resource_id=visit_id,
        ip_address=ip,
        user_agent=user_agent,
        user_id=provider_user_id,
        extra_context={"patient_name": patient_name, "zipzign_request_id": str(request_id)},
    )

    return {"status": "pending", "zipzign_request_id": str(request_id)}


async def handle_zipzign_webhook(
    payload: dict,
    db: AsyncSession,
    audit: AuditLogger,
) -> None:
    """Process a ZipZign webhook event (signed / declined) and update the visit MA 91 status."""
    event = payload.get("event", "")
    metadata = payload.get("metadata") or {}
    visit_id_str = metadata.get("visit_id")

    if not visit_id_str:
        logger.warning("ZipZign webhook missing visit_id in metadata: %s", payload)
        return

    try:
        visit_id = uuid.UUID(visit_id_str)
    except ValueError:
        logger.warning("ZipZign webhook invalid visit_id: %s", visit_id_str)
        return

    result = await db.execute(select(Visit).where(Visit.id == visit_id))
    visit = result.scalar_one_or_none()
    if not visit:
        logger.warning("ZipZign webhook: visit %s not found", visit_id)
        return

    if event == "signed":
        visit.ma91_status = "signed"
        visit.ma91_signed_at = datetime.now(timezone.utc)
    elif event == "declined":
        visit.ma91_status = "declined"
    else:
        logger.info("ZipZign webhook unhandled event '%s' for visit %s", event, visit_id)
        return

    await db.commit()

    await audit.log(
        action="MA91_WEBHOOK_RECEIVED",
        resource_type="visit",
        resource_id=visit_id,
        ip_address=None,
        user_agent=None,
        user_id=None,
        extra_context={"event": event},
    )


def _build_ma91_html(
    provider_name: str,
    provider_npi: str,
    patient_name: str,
    visit_date: str,
) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: Arial, sans-serif; font-size: 14px; color: #111; margin: 40px; }}
    h1 {{ font-size: 18px; text-align: center; margin-bottom: 4px; }}
    .subtitle {{ text-align: center; font-size: 12px; color: #555; margin-bottom: 24px; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
    td {{ padding: 6px 10px; border: 1px solid #ccc; }}
    .label {{ font-weight: bold; width: 40%; background: #f9f9f9; }}
    .cert-box {{ border: 2px solid #333; padding: 16px; margin: 24px 0; background: #fffbe6; }}
    .cert-box p {{ margin: 0; line-height: 1.6; }}
    .sig-area {{ margin-top: 40px; }}
    .sig-line {{ border-top: 1px solid #333; margin-top: 60px; padding-top: 6px; font-size: 12px; color: #555; }}
  </style>
</head>
<body>
  <h1>MA 91 — Encounter Form Certification</h1>
  <p class="subtitle">Pennsylvania Medicaid — Type 13 Doula Services</p>

  <table>
    <tr><td class="label">Provider Name</td><td>{provider_name}</td></tr>
    <tr><td class="label">Provider NPI</td><td>{provider_npi}</td></tr>
    <tr><td class="label">Patient Name</td><td>{patient_name}</td></tr>
    <tr><td class="label">Date of Service</td><td>{visit_date}</td></tr>
  </table>

  <div class="cert-box">
    <p>{MA91_TEXT}</p>
  </div>

  <div class="sig-area">
    <div class="sig-line">Patient Signature &amp; Date</div>
  </div>
</body>
</html>"""

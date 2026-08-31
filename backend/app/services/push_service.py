"""Web Push notification service using VAPID + pywebpush."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.push_subscription import PushSubscription

log = logging.getLogger(__name__)


def _send_one(endpoint: str, p256dh: str, auth: str, payload: str) -> None:
    """Synchronous pywebpush call — run in a thread pool."""
    try:
        from pywebpush import webpush, WebPushException  # type: ignore[import]
        webpush(
            subscription_info={"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}},
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": settings.VAPID_CLAIMS_EMAIL},
            content_encoding="aes128gcm",
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("Push delivery failed for %s: %s", endpoint[:60], exc)


async def _send_to_user(db: AsyncSession, user_id: uuid.UUID, title: str, body: str, url: str = "/") -> None:
    """Push a notification to all subscriptions for one user."""
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        return

    result = await db.execute(select(PushSubscription).where(PushSubscription.user_id == user_id))
    subs = result.scalars().all()
    if not subs:
        return

    payload = json.dumps({"title": title, "body": body, "url": url})
    tasks = [
        asyncio.to_thread(_send_one, s.endpoint, s.p256dh_key, s.auth_key, payload)
        for s in subs
    ]
    await asyncio.gather(*tasks, return_exceptions=True)


async def _send_to_role(db: AsyncSession, role: str, title: str, body: str, url: str = "/") -> None:
    """Push a notification to all subscriptions for every user with a given role."""
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        return

    from app.models.user import User
    user_ids_result = await db.execute(select(User.id).where(User.role == role))
    user_ids = [row[0] for row in user_ids_result.all()]

    result = await db.execute(
        select(PushSubscription).where(PushSubscription.user_id.in_(user_ids))
    )
    subs = result.scalars().all()
    if not subs:
        return

    payload = json.dumps({"title": title, "body": body, "url": url})
    tasks = [
        asyncio.to_thread(_send_one, s.endpoint, s.p256dh_key, s.auth_key, payload)
        for s in subs
    ]
    await asyncio.gather(*tasks, return_exceptions=True)


# ── Public helpers called from route / service layer ─────────────────────────

async def notify_claim_status(db: AsyncSession, provider_id: uuid.UUID, status: str, patient_name: str) -> None:
    status_lower = (status or "").lower()
    if status_lower in ("paid", "approved", "accepted"):
        title = "Claim approved"
        body = f"Your claim for {patient_name} was approved."
        url = "/reports"
    elif status_lower in ("denied", "rejected"):
        title = "Claim denied"
        body = f"Your claim for {patient_name} was denied. Review for resubmission."
        url = "/reports"
    else:
        return
    try:
        await _send_to_user(db, provider_id, title, body, url)
    except Exception:  # noqa: BLE001
        log.warning("notify_claim_status failed", exc_info=True)


async def notify_billing_admin_new_claim(db: AsyncSession, billing_provider_id: uuid.UUID, patient_name: str) -> None:
    """Notify billing admins in a billing entity that a new claim needs review."""
    try:
        from app.models.user import User
        result = await db.execute(
            select(User.id).where(
                User.billing_provider_id == billing_provider_id,
                User.role == "billing_admin",
            )
        )
        for (uid,) in result.all():
            await _send_to_user(db, uid, "New claim pending review", f"A claim for {patient_name} is ready for billing review.", "/billing-admin/claims")
    except Exception:  # noqa: BLE001
        log.warning("notify_billing_admin_new_claim failed", exc_info=True)


async def notify_admins_new_lead(db: AsyncSession, lead_name: str, lead_email: str) -> None:
    try:
        await _send_to_role(db, "admin", "New doula lead", f"{lead_name} ({lead_email}) submitted an inquiry.", "/admin/leads")
    except Exception:  # noqa: BLE001
        log.warning("notify_admins_new_lead failed", exc_info=True)


async def notify_enrollment_stage(db: AsyncSession, provider_id: uuid.UUID, stage: str) -> None:
    stage_labels = {
        "pcb": "PCB Certification",
        "nppes": "NPPES / NPI Setup",
        "promise": "PROMISe™ Enrollment",
        "mco": "MCO Contracting",
    }
    label = stage_labels.get(stage.lower(), stage)
    try:
        await _send_to_user(
            db, provider_id,
            f"{label} completed",
            f"Your {label} stage has been marked complete. Check your Enrollment Status for next steps.",
            "/enrollment-status",
        )
    except Exception:  # noqa: BLE001
        log.warning("notify_enrollment_stage failed", exc_info=True)


async def notify_caqh_reminders(db: AsyncSession) -> None:
    """Daily job: push reminders for upcoming CAQH attestation deadlines."""
    try:
        from datetime import date, timedelta
        from app.models.enrollment import EnrollmentService
        cutoff = date.today() + timedelta(days=30)
        result = await db.execute(
            select(EnrollmentService.provider_id).where(
                EnrollmentService.caqh_attestation_due != None,  # noqa: E711
                EnrollmentService.caqh_attestation_due <= cutoff,
            )
        )
        for (uid,) in result.all():
            await _send_to_user(
                db, uid,
                "CAQH attestation due soon",
                "Your CAQH attestation is due within 30 days. Log in to complete it.",
                "/enrollment-status",
            )
    except Exception:  # noqa: BLE001
        log.warning("notify_caqh_reminders failed", exc_info=True)


async def notify_filing_deadline_reminders(db: AsyncSession) -> None:
    """Daily job: push reminders for claims approaching their 180-day filing deadline."""
    try:
        from datetime import date, timedelta
        from app.models.claim import Claim
        warning_date = date.today() + timedelta(days=14)
        cutoff_date = date.today() + timedelta(days=180)
        result = await db.execute(
            select(Claim.provider_id, Claim.id).where(
                Claim.status.in_(["pending", "draft"]),
                Claim.service_date != None,  # noqa: E711
                Claim.service_date >= date.today(),
                Claim.service_date <= warning_date,
            )
        )
        providers_notified: set[uuid.UUID] = set()
        for (uid, _) in result.all():
            if uid not in providers_notified:
                providers_notified.add(uid)
                await _send_to_user(
                    db, uid,
                    "Claim filing deadline approaching",
                    "You have claims approaching the 180-day Medicaid filing deadline. Submit soon.",
                    "/reports",
                )
    except Exception:  # noqa: BLE001
        log.warning("notify_filing_deadline_reminders failed", exc_info=True)

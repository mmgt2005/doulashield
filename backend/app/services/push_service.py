"""Web Push notification service using VAPID + pywebpush."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid

from sqlalchemy import select, update
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


# ── Scheduled daily / interval jobs ──────────────────────────────────────────

async def notify_visit_reminders(db: AsyncSession) -> None:
    """Interval job (every 15 min): push 60-min and 30-min visit reminders to providers."""
    try:
        from datetime import datetime, timedelta, timezone
        from app.models.visit import Visit

        now = datetime.now(tz=timezone.utc)

        # 60-minute reminder window: scheduled_at 55–65 min from now
        window_60_lo = now + timedelta(minutes=55)
        window_60_hi = now + timedelta(minutes=65)
        result_60 = await db.execute(
            select(Visit.id, Visit.provider_id, Visit.visit_type).where(
                Visit.scheduled_at >= window_60_lo,
                Visit.scheduled_at <= window_60_hi,
                Visit.reminder_60min_sent.is_(False),
            )
        )
        for (vid, uid, vtype) in result_60.all():
            label = vtype.replace("_", " ").title()
            await _send_to_user(
                db, uid,
                "Visit in 1 hour",
                f"Your {label} visit is scheduled in about 1 hour.",
                "/clients",
            )
            await db.execute(
                update(Visit).where(Visit.id == vid).values(reminder_60min_sent=True)
            )
        await db.commit()

        # 30-minute reminder window: scheduled_at 25–35 min from now
        window_30_lo = now + timedelta(minutes=25)
        window_30_hi = now + timedelta(minutes=35)
        result_30 = await db.execute(
            select(Visit.id, Visit.provider_id, Visit.visit_type).where(
                Visit.scheduled_at >= window_30_lo,
                Visit.scheduled_at <= window_30_hi,
                Visit.reminder_30min_sent.is_(False),
            )
        )
        for (vid, uid, vtype) in result_30.all():
            label = vtype.replace("_", " ").title()
            await _send_to_user(
                db, uid,
                "Visit in 30 minutes",
                f"Your {label} visit is starting in 30 minutes.",
                "/clients",
            )
            await db.execute(
                update(Visit).where(Visit.id == vid).values(reminder_30min_sent=True)
            )
        await db.commit()
    except Exception:  # noqa: BLE001
        log.warning("notify_visit_reminders failed", exc_info=True)


async def notify_soap_note_reminder(db: AsyncSession) -> None:
    """Daily job: remind providers to complete SOAP notes for visits that ended 2–26 hours ago."""
    try:
        from datetime import datetime, timedelta, timezone
        from app.models.visit import Visit

        now = datetime.now(tz=timezone.utc)
        lo = now - timedelta(hours=26)
        hi = now - timedelta(hours=2)

        result = await db.execute(
            select(Visit.provider_id, Visit.visit_type).where(
                Visit.visit_ended_at >= lo,
                Visit.visit_ended_at <= hi,
                Visit.subjective.is_(None),
                Visit.objective.is_(None),
                Visit.assessment.is_(None),
                Visit.plan.is_(None),
            )
        )
        notified: set[uuid.UUID] = set()
        for (uid, vtype) in result.all():
            if uid not in notified:
                notified.add(uid)
                await _send_to_user(
                    db, uid,
                    "SOAP note not yet submitted",
                    "You have a recent visit with no SOAP notes. Please complete documentation.",
                    "/clients",
                )
    except Exception:  # noqa: BLE001
        log.warning("notify_soap_note_reminder failed", exc_info=True)


async def notify_ma91_pending(db: AsyncSession) -> None:
    """Daily job: remind providers of visits where the MA 91 signature is still pending."""
    try:
        from datetime import datetime, timedelta, timezone
        from app.models.visit import Visit

        now = datetime.now(tz=timezone.utc)
        # Visits that ended between 1 hour and 7 days ago without a signed MA 91
        lo = now - timedelta(days=7)
        hi = now - timedelta(hours=1)

        result = await db.execute(
            select(Visit.provider_id).where(
                Visit.visit_ended_at >= lo,
                Visit.visit_ended_at <= hi,
                Visit.ma91_signed_at.is_(None),
                Visit.ma91_status.notin_(["signed", "completed", "not_required"]),
            )
        )
        notified: set[uuid.UUID] = set()
        for (uid,) in result.all():
            if uid not in notified:
                notified.add(uid)
                await _send_to_user(
                    db, uid,
                    "MA 91 signature pending",
                    "One or more recent visits still need a client MA 91 signature.",
                    "/clients",
                )
    except Exception:  # noqa: BLE001
        log.warning("notify_ma91_pending failed", exc_info=True)


async def notify_prior_auth_expiring(db: AsyncSession) -> None:
    """Daily job: notify providers of prior authorizations expiring within 30 days."""
    try:
        from datetime import date, timedelta
        from app.models.prior_authorization import PriorAuthorization

        today = date.today()
        cutoff = today + timedelta(days=30)

        result = await db.execute(
            select(PriorAuthorization.provider_id).where(
                PriorAuthorization.end_date >= today,
                PriorAuthorization.end_date <= cutoff,
                PriorAuthorization.status.notin_(["denied", "expired", "cancelled"]),
            )
        )
        notified: set[uuid.UUID] = set()
        for (uid,) in result.all():
            if uid not in notified:
                notified.add(uid)
                await _send_to_user(
                    db, uid,
                    "Prior authorization expiring soon",
                    "One or more prior authorizations expire within 30 days. Review and renew if needed.",
                    "/clients",
                )
    except Exception:  # noqa: BLE001
        log.warning("notify_prior_auth_expiring failed", exc_info=True)


async def notify_stale_claims_billing(db: AsyncSession) -> None:
    """Daily job: notify billing admins of claims that have been pending for 3+ days without review."""
    try:
        from datetime import datetime, timedelta, timezone
        from app.models.claim import Claim
        from app.models.user import User

        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=3)

        result = await db.execute(
            select(Claim.provider_id).where(
                Claim.status == "pending",
                Claim.submitted_at <= cutoff,
            )
        )
        provider_ids = {row[0] for row in result.all() if row[0]}
        if not provider_ids:
            return

        # Find billing_provider_ids for these providers
        bp_result = await db.execute(
            select(User.billing_provider_id).where(
                User.id.in_(provider_ids),
                User.billing_provider_id.isnot(None),
            )
        )
        billing_provider_ids = {row[0] for row in bp_result.all() if row[0]}
        if not billing_provider_ids:
            return

        # Notify the billing admins who manage those billing providers
        admin_result = await db.execute(
            select(User.id).where(
                User.role == "billing_admin",
                User.managed_billing_provider_id.in_(billing_provider_ids),
            )
        )
        for (uid,) in admin_result.all():
            await _send_to_user(
                db, uid,
                "Claims pending review",
                "One or more claims have been awaiting billing review for 3+ days.",
                "/billing-admin/claims",
            )
    except Exception:  # noqa: BLE001
        log.warning("notify_stale_claims_billing failed", exc_info=True)


async def notify_stale_leads(db: AsyncSession) -> None:
    """Daily job: notify admins of leads that have not been contacted within 48 hours."""
    try:
        from datetime import datetime, timedelta, timezone
        from app.models.lead import Lead

        cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=48)

        result = await db.execute(
            select(Lead.id).where(
                Lead.status == "new",
                Lead.created_at <= cutoff,
                Lead.is_demo.is_(False),
            )
        )
        count = len(result.all())
        if count:
            await _send_to_role(
                db, "admin",
                "Leads not yet contacted",
                f"{count} lead{'s' if count != 1 else ''} submitted over 48 hours ago with no follow-up.",
                "/admin/leads",
            )
    except Exception:  # noqa: BLE001
        log.warning("notify_stale_leads failed", exc_info=True)


async def notify_caqh_reminders(db: AsyncSession) -> None:
    """Daily job: push reminders for upcoming CAQH annual attestation deadlines."""
    try:
        from datetime import date, timedelta
        from app.models.enrollment import EnrollmentService

        today = date.today()
        cutoff = today + timedelta(days=30)

        # CAQH attestation is due annually from the PCB certification date.
        # Compute the next anniversary and alert when it falls within 30 days.
        result = await db.execute(
            select(EnrollmentService.provider_id, EnrollmentService.pcb_cert_date).where(
                EnrollmentService.pcb_cert_date.isnot(None),
            )
        )
        for (uid, cert_date) in result.all():
            if cert_date is None:
                continue
            try:
                due = cert_date.replace(year=today.year)
            except ValueError:
                due = cert_date.replace(year=today.year, day=28)
            if due < today:
                try:
                    due = due.replace(year=today.year + 1)
                except ValueError:
                    due = due.replace(year=today.year + 1, day=28)
            if due <= cutoff:
                await _send_to_user(
                    db, uid,
                    "CAQH attestation due soon",
                    "Your CAQH annual attestation is due within 30 days. Log in to complete it.",
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
        result = await db.execute(
            select(Claim.provider_id, Claim.id).where(
                Claim.status.in_(["pending", "draft"]),
                Claim.service_date.isnot(None),
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

import logging
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Annotated

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.future import select

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.middleware import AuditMiddleware, SecurityHeadersMiddleware

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
)

_VERSION = Path(__file__).parent.parent.joinpath("VERSION").read_text().strip()
_sync_logger = logging.getLogger("doulashield.remittance_sync")
_caqh_logger = logging.getLogger("doulashield.caqh_reminder")
_promise_logger = logging.getLogger("doulashield.promise_reminder")
_pcb_logger = logging.getLogger("doulashield.pcb_reminder")
_liability_logger = logging.getLogger("doulashield.liability_reminder")
_ma589_logger = logging.getLogger("doulashield.ma589_reminder")
_claim_deadline_logger = logging.getLogger("doulashield.claim_deadline")


async def _run_daily_remittance_sync() -> None:
    """
    Fetch 30-day rolling remittances for every provider with Availity credentials.
    Each provider runs in its own DB session so one failure does not block others.
    """
    from app.core.audit import AuditLogger
    from app.dependencies import _AsyncSession
    from app.models.user import User
    from app.schemas.remittance import RemittanceFetchRequest
    from app.services.remittance_service import RemittanceService

    _sync_logger.info("daily_remittance_sync: starting")
    today = date.today()
    start = today - timedelta(days=30)
    fetch_req = RemittanceFetchRequest(start_date=start, end_date=today)

    async with _AsyncSession() as db:
        result = await db.execute(
            select(User).where(
                User.availity_client_id_encrypted.isnot(None),
                User.is_active.is_(True),
            )
        )
        providers = result.scalars().all()

    _sync_logger.info("daily_remittance_sync: found %d providers to sync", len(providers))

    for provider in providers:
        try:
            async with _AsyncSession() as db:
                audit = AuditLogger(db)
                svc = RemittanceService(db, audit)
                saved = await svc.fetch_remittances(
                    requesting_user_id=provider.id,
                    data=fetch_req,
                    ip=None,
                    user_agent="daily-remittance-sync/1.0",
                )
            _sync_logger.info(
                "daily_remittance_sync: provider=%s fetched=%d remittances",
                provider.id,
                len(saved),
            )
        except Exception as exc:
            _sync_logger.error(
                "daily_remittance_sync: provider=%s FAILED: %s",
                provider.id,
                exc,
                exc_info=True,
            )

    _sync_logger.info("daily_remittance_sync: done")


_CAQH_REMINDER_DAYS = {30, 14, 7, 0, -1, -2, -3, -4, -5, -6, -7}


async def _run_caqh_reminder_check() -> None:
    """
    Send CAQH re-attestation reminder emails to providers whose 90-day window
    is at 30, 14, 7, or 0 days remaining, and daily for the first 7 days overdue.
    Each provider runs in its own DB session so one failure does not block others.
    """
    from app.dependencies import _AsyncSession
    from app.models.user import User
    from app.services.email_service import send_caqh_reminder_email

    _caqh_logger.info("caqh_reminder_check: starting")

    async with _AsyncSession() as db:
        from sqlalchemy.future import select as _select
        result = await db.execute(
            _select(User).where(
                User.is_active.is_(True),
                User.caqh_last_attested_on.isnot(None),
                User.role == "provider",
            )
        )
        providers = result.scalars().all()

    _caqh_logger.info("caqh_reminder_check: found %d providers with CAQH date", len(providers))

    today = date.today()
    sent = 0
    for provider in providers:
        try:
            expiry = provider.caqh_last_attested_on + timedelta(days=90)
            days_remaining = (expiry - today).days
            if days_remaining not in _CAQH_REMINDER_DAYS:
                continue
            name = provider.full_name or provider.email
            await send_caqh_reminder_email(provider.email, name, days_remaining)
            sent += 1
            _caqh_logger.info(
                "caqh_reminder_check: sent reminder to provider=%s days_remaining=%d",
                provider.id,
                days_remaining,
            )
        except Exception as exc:
            _caqh_logger.error(
                "caqh_reminder_check: provider=%s FAILED: %s",
                provider.id,
                exc,
                exc_info=True,
            )

    _caqh_logger.info("caqh_reminder_check: done sent=%d", sent)


_PROMISE_REMINDER_DAYS = {365, 180, 90, 30, 14, 7, 0, -1, -2, -3, -4, -5, -6, -7}
_PCB_REMINDER_DAYS = {60, 30, 14, 7, 0, -1, -2, -3, -4, -5, -6, -7}
_LIABILITY_REMINDER_DAYS = {30, 14, 7, 0, -1, -2, -3, -4, -5, -6, -7}


async def _run_promise_reminder_check() -> None:
    """
    Send PROMISe™ re-enrollment reminder emails to providers whose 5-year window
    is at 365, 180, 90, 30, 14, 7, or 0 days remaining, and daily for the first 7 days overdue.
    Each provider runs in its own DB session so one failure does not block others.
    """
    from app.dependencies import _AsyncSession
    from app.models.user import User
    from app.services.email_service import send_promise_reminder_email

    _promise_logger.info("promise_reminder_check: starting")

    async with _AsyncSession() as db:
        from sqlalchemy.future import select as _select
        result = await db.execute(
            _select(User).where(
                User.is_active.is_(True),
                User.promise_last_enrolled_on.isnot(None),
                User.role == "provider",
            )
        )
        providers = result.scalars().all()

    _promise_logger.info("promise_reminder_check: found %d providers with PROMISe date", len(providers))

    today = date.today()
    sent = 0
    for provider in providers:
        try:
            expiry = provider.promise_last_enrolled_on + timedelta(days=1825)
            days_remaining = (expiry - today).days
            if days_remaining not in _PROMISE_REMINDER_DAYS:
                continue
            name = provider.full_name or provider.email
            await send_promise_reminder_email(provider.email, name, days_remaining)
            sent += 1
            _promise_logger.info(
                "promise_reminder_check: sent reminder to provider=%s days_remaining=%d",
                provider.id,
                days_remaining,
            )
        except Exception as exc:
            _promise_logger.error(
                "promise_reminder_check: provider=%s FAILED: %s",
                provider.id,
                exc,
                exc_info=True,
            )

    _promise_logger.info("promise_reminder_check: done sent=%d", sent)


async def _run_pcb_reminder_check() -> None:
    """
    Send PCB Perinatal Certification renewal reminders at 60, 30, 14, 7, 0 days before expiry
    and daily for the first 7 days overdue (2-year cycle = 730 days).
    """
    from app.dependencies import _AsyncSession
    from app.models.user import User
    from app.services.email_service import send_pcb_reminder_email

    _pcb_logger.info("pcb_reminder_check: starting")

    async with _AsyncSession() as db:
        from sqlalchemy.future import select as _select
        result = await db.execute(
            _select(User).where(
                User.is_active.is_(True),
                User.pcb_last_certified_on.isnot(None),
                User.role == "provider",
            )
        )
        providers = result.scalars().all()

    _pcb_logger.info("pcb_reminder_check: found %d providers with PCB date", len(providers))

    today = date.today()
    sent = 0
    for provider in providers:
        try:
            expiry = provider.pcb_last_certified_on + timedelta(days=730)
            days_remaining = (expiry - today).days
            if days_remaining not in _PCB_REMINDER_DAYS:
                continue
            name = provider.full_name or provider.email
            await send_pcb_reminder_email(provider.email, name, days_remaining)
            sent += 1
            _pcb_logger.info(
                "pcb_reminder_check: sent reminder to provider=%s days_remaining=%d",
                provider.id,
                days_remaining,
            )
        except Exception as exc:
            _pcb_logger.error(
                "pcb_reminder_check: provider=%s FAILED: %s",
                provider.id,
                exc,
                exc_info=True,
            )

    _pcb_logger.info("pcb_reminder_check: done sent=%d", sent)


async def _run_liability_reminder_check() -> None:
    """
    Send liability insurance expiry reminders at 30, 14, 7, 0 days before expiry
    and daily for the first 7 days after expiry.
    """
    from app.dependencies import _AsyncSession
    from app.models.user import User
    from app.services.email_service import send_liability_reminder_email

    _liability_logger.info("liability_reminder_check: starting")

    async with _AsyncSession() as db:
        from sqlalchemy.future import select as _select
        result = await db.execute(
            _select(User).where(
                User.is_active.is_(True),
                User.liability_insurance_expires_on.isnot(None),
                User.role == "provider",
            )
        )
        providers = result.scalars().all()

    _liability_logger.info("liability_reminder_check: found %d providers with liability date", len(providers))

    today = date.today()
    sent = 0
    for provider in providers:
        try:
            days_remaining = (provider.liability_insurance_expires_on - today).days
            if days_remaining not in _LIABILITY_REMINDER_DAYS:
                continue
            name = provider.full_name or provider.email
            await send_liability_reminder_email(provider.email, name, days_remaining)
            sent += 1
            _liability_logger.info(
                "liability_reminder_check: sent reminder to provider=%s days_remaining=%d",
                provider.id,
                days_remaining,
            )
        except Exception as exc:
            _liability_logger.error(
                "liability_reminder_check: provider=%s FAILED: %s",
                provider.id,
                exc,
                exc_info=True,
            )

    _liability_logger.info("liability_reminder_check: done sent=%d", sent)


async def _run_ma589_reminder_check() -> None:
    """
    Send MA 589 reminders to providers who have patients with prenatal visits started
    but no ma589_signed_date recorded. Fires once per day; each patient is only
    notified once (not repeatedly) — tracked by checking if a prenatal visit exists
    and the signed date is still null.
    """
    from app.core.encryption import decrypt_field
    from app.dependencies import _AsyncSession
    from app.models.patient import Patient
    from app.models.user import User
    from app.models.visit import Visit
    from app.services.email_service import send_ma589_reminder_email

    _ma589_logger.info("ma589_reminder_check: starting")

    async with _AsyncSession() as db:
        from sqlalchemy import and_
        from sqlalchemy.future import select as _select

        # Find patients with a prenatal_1 visit started but no MA 589 signed date
        result = await db.execute(
            _select(Patient, User)
            .join(User, User.id == Patient.provider_id)
            .join(
                Visit,
                and_(
                    Visit.patient_id == Patient.id,
                    Visit.visit_type == "prenatal_1",
                    Visit.visit_started_at.isnot(None),
                ),
            )
            .where(
                Patient.is_active.is_(True),
                Patient.ma589_signed_date.is_(None),
                User.is_active.is_(True),
                User.role == "provider",
            )
        )
        rows = result.all()

    _ma589_logger.info("ma589_reminder_check: found %d patients missing MA 589", len(rows))

    sent = 0
    for patient, provider in rows:
        try:
            patient_name = decrypt_field(patient.name_encrypted)
            provider_name = provider.full_name or provider.email
            await send_ma589_reminder_email(provider.email, provider_name, patient_name)
            sent += 1
            _ma589_logger.info(
                "ma589_reminder_check: sent reminder to provider=%s for patient=%s",
                provider.id,
                patient.id,
            )
        except Exception as exc:
            _ma589_logger.error(
                "ma589_reminder_check: provider=%s patient=%s FAILED: %s",
                provider.id,
                patient.id,
                exc,
                exc_info=True,
            )

    _ma589_logger.info("ma589_reminder_check: done sent=%d", sent)


# 150 days remaining = 30 days since service = best-practice nudge
_CLAIM_INITIAL_REMINDER_DAYS = {150, 90, 60, 30, 14, 7, 0, -1, -2, -3, -4, -5, -6, -7}
# 335 days remaining = 30 days since service = best-practice nudge for corrected claims
_CLAIM_CORRECTED_REMINDER_DAYS = {335, 180, 90, 30, 14, 7, 0, -1, -2, -3, -4, -5, -6, -7}
_CLAIM_SECONDARY_REMINDER_DAYS = {30, 14, 7, 0, -1, -2, -3, -4, -5, -6, -7}


async def _run_claim_deadline_check() -> None:
    """
    Send PA Medicaid claim filing deadline reminders for three deadline types:
    A) Initial unfiled claims — 180-day deadline from service_date
    B) Corrected/resubmitted claims — 365-day deadline from service_date
    C) Secondary claims (other insurance) — 60-day deadline from EOB payment_date
    """
    from app.core.encryption import decrypt_field
    from app.dependencies import _AsyncSession
    from app.models.claim import Claim
    from app.models.patient import Patient
    from app.models.remittance import Remittance
    from app.models.user import User
    from app.services.email_service import send_claim_deadline_email
    from sqlalchemy import and_
    from sqlalchemy.future import select as _select

    _claim_deadline_logger.info("claim_deadline_check: starting")

    today = date.today()

    def _initials(full_name: str) -> str:
        parts = full_name.strip().split()
        if len(parts) >= 2:
            return f"{parts[0][0].upper()}. {parts[-1][0].upper()}."
        return f"{full_name[0].upper()}." if full_name else "?"

    # ── Loop A: initial unfiled claims ───────────────────────────────────────
    async with _AsyncSession() as db:
        result = await db.execute(
            _select(Claim, Patient, User)
            .join(Patient, Patient.id == Claim.patient_id)
            .join(User, User.id == Claim.provider_id)
            .where(
                Claim.submitted_at.is_(None),
                Claim.status.notin_(["paid"]),
                Claim.service_date.isnot(None),
                User.is_active.is_(True),
                User.role == "provider",
            )
        )
        initial_rows = result.all()

    sent_a = 0
    for claim, patient, provider in initial_rows:
        try:
            days_remaining = 180 - (today - claim.service_date).days
            if days_remaining not in _CLAIM_INITIAL_REMINDER_DAYS:
                continue
            patient_name = decrypt_field(patient.name_encrypted)
            initials = _initials(patient_name)
            provider_name = provider.full_name or provider.email
            await send_claim_deadline_email(
                provider.email, provider_name, initials,
                claim.visit_type or "unknown", str(claim.service_date),
                days_remaining, "initial",
            )
            sent_a += 1
            _claim_deadline_logger.info(
                "claim_deadline_check: initial claim=%s provider=%s days_remaining=%d",
                claim.id, provider.id, days_remaining,
            )
        except Exception as exc:
            _claim_deadline_logger.error(
                "claim_deadline_check: initial claim=%s FAILED: %s",
                claim.id, exc, exc_info=True,
            )

    _claim_deadline_logger.info("claim_deadline_check: initial loop done sent=%d", sent_a)

    # ── Loop B: corrected / resubmitted claims ────────────────────────────────
    async with _AsyncSession() as db:
        result = await db.execute(
            _select(Claim, Patient, User)
            .join(Patient, Patient.id == Claim.patient_id)
            .join(User, User.id == Claim.provider_id)
            .where(
                Claim.resubmit_count > 0,
                Claim.status.notin_(["paid"]),
                Claim.service_date.isnot(None),
                User.is_active.is_(True),
                User.role == "provider",
            )
        )
        corrected_rows = result.all()

    sent_b = 0
    for claim, patient, provider in corrected_rows:
        try:
            days_remaining = 365 - (today - claim.service_date).days
            if days_remaining not in _CLAIM_CORRECTED_REMINDER_DAYS:
                continue
            patient_name = decrypt_field(patient.name_encrypted)
            initials = _initials(patient_name)
            provider_name = provider.full_name or provider.email
            await send_claim_deadline_email(
                provider.email, provider_name, initials,
                claim.visit_type or "unknown", str(claim.service_date),
                days_remaining, "corrected",
            )
            sent_b += 1
            _claim_deadline_logger.info(
                "claim_deadline_check: corrected claim=%s provider=%s days_remaining=%d",
                claim.id, provider.id, days_remaining,
            )
        except Exception as exc:
            _claim_deadline_logger.error(
                "claim_deadline_check: corrected claim=%s FAILED: %s",
                claim.id, exc, exc_info=True,
            )

    _claim_deadline_logger.info("claim_deadline_check: corrected loop done sent=%d", sent_b)

    # ── Loop C: secondary claims (other insurance, 60 days from EOB) ──────────
    async with _AsyncSession() as db:
        result = await db.execute(
            _select(Claim, Patient, User, Remittance)
            .join(Patient, Patient.id == Claim.patient_id)
            .join(User, User.id == Claim.provider_id)
            .join(Remittance, Remittance.id == Claim.remittance_id)
            .where(
                Patient.has_other_insurance.is_(True),
                Claim.remittance_id.isnot(None),
                Claim.status.notin_(["paid"]),
                Remittance.payment_date.isnot(None),
                User.is_active.is_(True),
                User.role == "provider",
            )
        )
        secondary_rows = result.all()

    sent_c = 0
    for claim, patient, provider, remittance in secondary_rows:
        try:
            days_remaining = 60 - (today - remittance.payment_date).days
            if days_remaining not in _CLAIM_SECONDARY_REMINDER_DAYS:
                continue
            patient_name = decrypt_field(patient.name_encrypted)
            initials = _initials(patient_name)
            provider_name = provider.full_name or provider.email
            await send_claim_deadline_email(
                provider.email, provider_name, initials,
                claim.visit_type or "unknown", str(claim.service_date or remittance.payment_date),
                days_remaining, "secondary",
            )
            sent_c += 1
            _claim_deadline_logger.info(
                "claim_deadline_check: secondary claim=%s provider=%s days_remaining=%d",
                claim.id, provider.id, days_remaining,
            )
        except Exception as exc:
            _claim_deadline_logger.error(
                "claim_deadline_check: secondary claim=%s FAILED: %s",
                claim.id, exc, exc_info=True,
            )

    _claim_deadline_logger.info(
        "claim_deadline_check: done initial=%d corrected=%d secondary=%d",
        sent_a, sent_b, sent_c,
    )


_FILING_REMINDER_DAYS = {30, 14, 7, 3, 1, 0}
_filing_logger = logging.getLogger("doulashield.filing_deadline")


async def _run_filing_deadline_check() -> None:
    """
    Send timely-filing deadline reminders for claims not yet paid/denied at
    30, 14, 7, 3, 1, and 0 days before the filing deadline.
    """
    from app.core.encryption import decrypt_field
    from app.dependencies import _AsyncSession
    from app.models.claim import Claim
    from app.models.patient import Patient
    from app.models.user import User
    from app.services.email_service import send_filing_deadline_reminder_email

    _filing_logger.info("filing_deadline_check: starting")

    async with _AsyncSession() as db:
        from sqlalchemy.future import select as _select

        result = await db.execute(
            _select(Claim, User, Patient)
            .join(User, User.id == Claim.provider_id)
            .join(Patient, Patient.id == Claim.patient_id)
            .where(
                Claim.filing_deadline_date.isnot(None),
                Claim.status.notin_(["paid", "denied"]),
                User.is_active.is_(True),
            )
        )
        rows = result.all()

    _filing_logger.info("filing_deadline_check: found %d open claims with deadline", len(rows))

    today = date.today()
    sent = 0
    for claim, provider, patient in rows:
        try:
            days = (claim.filing_deadline_date - today).days
            if days not in _FILING_REMINDER_DAYS:
                continue
            patient_name = decrypt_field(patient.name_encrypted)
            provider_name = provider.full_name or provider.email
            svc_date = claim.service_date.isoformat() if claim.service_date else "unknown"
            claim_url = (
                f"{settings.FRONTEND_ORIGIN}/clients/{patient.id}"
                f"/visits/{claim.visit_type}"
            )
            await send_filing_deadline_reminder_email(
                provider.email, provider_name, patient_name, days, svc_date, claim_url
            )
            sent += 1
            _filing_logger.info(
                "filing_deadline_check: sent reminder to provider=%s claim=%s days=%d",
                provider.id, claim.id, days,
            )
        except Exception as exc:
            _filing_logger.error(
                "filing_deadline_check: claim=%s FAILED: %s",
                claim.id, exc, exc_info=True,
            )

    _filing_logger.info("filing_deadline_check: done sent=%d", sent)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # hour=7 UTC ≈ 02:00 ET; avoids pytz dependency for named timezone strings
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _run_daily_remittance_sync,
        trigger="cron",
        hour=7,
        minute=0,
        id="daily_remittance_sync",
        replace_existing=True,
        misfire_grace_time=3600,  # tolerate up to 1h late start on Railway cold boot
    )
    scheduler.add_job(
        _run_caqh_reminder_check,
        trigger="cron",
        hour=7,
        minute=30,
        id="caqh_reminder_check",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        _run_promise_reminder_check,
        trigger="cron",
        hour=7,
        minute=45,
        id="promise_reminder_check",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        _run_pcb_reminder_check,
        trigger="cron",
        hour=7,
        minute=55,
        id="pcb_reminder_check",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        _run_liability_reminder_check,
        trigger="cron",
        hour=8,
        minute=0,
        id="liability_reminder_check",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        _run_ma589_reminder_check,
        trigger="cron",
        hour=8,
        minute=5,
        id="ma589_reminder_check",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        _run_filing_deadline_check,
        trigger="cron",
        hour=8,
        minute=15,
        id="filing_deadline_check",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    _sync_logger.info(
        "APScheduler started — remittance sync 07:00, CAQH 07:30, PROMISe 07:45, "
        "PCB 07:55, Liability 08:00, MA589 08:05, filing deadline 08:15 UTC"
    )
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        _sync_logger.info("APScheduler shut down")


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="DoulaShield API",
    version=_VERSION,
    lifespan=_lifespan,
    # Disable interactive docs in production — no PHI in Swagger UI
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    redoc_url=None,
    openapi_url=None if settings.ENVIRONMENT == "production" else "/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_cors_origins = [settings.FRONTEND_ORIGIN]
if settings.CORS_EXTRA_ORIGINS:
    _cors_origins.extend(o.strip() for o in settings.CORS_EXTRA_ORIGINS.split(",") if o.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    # DELETE is intentionally omitted — soft-delete via PATCH only
    allow_methods=["GET", "POST", "PATCH", "PUT", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AuditMiddleware)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", include_in_schema=False)
async def health() -> dict:
    return {"status": "ok", "version": _VERSION}


@app.post("/internal/trigger-remittance-sync", include_in_schema=False)
async def trigger_remittance_sync(
    x_internal_secret: Annotated[str, Header()] = "",
) -> dict:
    """Manual trigger for the daily remittance sync job (ops/testing only)."""
    if not settings.INTERNAL_SECRET or x_internal_secret != settings.INTERNAL_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing X-Internal-Secret header",
        )
    import asyncio
    asyncio.create_task(_run_daily_remittance_sync())
    return {"status": "sync triggered"}

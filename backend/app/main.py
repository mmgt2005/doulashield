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
    scheduler.start()
    _sync_logger.info(
        "APScheduler started — remittance sync 07:00 UTC, CAQH check 07:30 UTC, PROMISe check 07:45 UTC"
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
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

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
                    ip="scheduler",
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
    scheduler.start()
    _sync_logger.info("APScheduler started — daily remittance sync at 07:00 UTC (≈ 02:00 ET)")
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

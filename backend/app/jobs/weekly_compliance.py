"""
Weekly compliance summary email job.

Called from endpoint: run_weekly_compliance(db)
Standalone: python -m app.jobs.weekly_compliance [--dry-run]
"""
from __future__ import annotations

import asyncio
import sys
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.future import select

from app.core.config import settings
from app.models.billing_provider import BillingProvider
from app.models.enrollment import EnrollmentService
from app.models.user import User
from app.services import email_service

# Warning thresholds (days before expiry)
_CAQH_CYCLE = 90
_PCB_CYCLE = 730
_PROMISE_CYCLE = 1825

_WARN = {
    "caqh": 60,
    "pcb": 180,
    "promise": 365,
    "liability": 90,
}

_COMPLETE_STATUSES = {"active", "complete", "completed"}

_STAGE_LABELS = {
    "nppes_setup": "NPI update pending",
    "pcb": "PCB certification in progress",
    "enrollment": "PROMISe™ enrollment pending",
    "mco_contracting": "MCO contracting pending",
}

_STAGES = ["pcb", "nppes_setup", "enrollment", "mco_contracting"]

_URGENCY_RANK = {"expired": 0, "critical": 1, "warning": 2, "action_needed": 3}


def _expiry_item(
    name: str, cred: str, ref_date: date | None, cycle: int, threshold: int, critical_threshold: int
) -> dict | None:
    if not ref_date:
        return None
    exp = ref_date + timedelta(days=cycle)
    days = (exp - date.today()).days
    if days <= 0:
        return {"label": f"{name}'s {cred}: expired {abs(days)} days ago", "urgency": "expired"}
    if days <= threshold:
        urgency = "critical" if days <= critical_threshold else "warning"
        return {"label": f"{name}'s {cred}: {days} days to renew", "urgency": urgency}
    return None


def _liability_item(name: str, exp_date: date | None) -> dict | None:
    if not exp_date:
        return None
    days = (exp_date - date.today()).days
    if days <= 0:
        return {"label": f"{name}'s liability insurance: expired {abs(days)} days ago", "urgency": "expired"}
    if days <= _WARN["liability"]:
        urgency = "critical" if days <= 14 else "warning"
        return {"label": f"{name}'s liability insurance: {days} days to renew", "urgency": urgency}
    return None


def _build_items(providers: list[User], services: list[EnrollmentService]) -> list[dict]:
    stage_map: dict = {}
    for svc in services:
        stage_map.setdefault(svc.provider_id, {})[svc.stage] = svc.status

    items: list[dict] = []
    for u in providers:
        name = u.full_name or u.email.split("@")[0]

        for item in [
            _expiry_item(name, "CAQH", u.caqh_last_attested_on, _CAQH_CYCLE, _WARN["caqh"], 15),
            _expiry_item(name, "PCB", u.pcb_last_certified_on, _PCB_CYCLE, _WARN["pcb"], 30),
            _expiry_item(name, "PROMISe™", u.promise_last_enrolled_on, _PROMISE_CYCLE, _WARN["promise"], 60),
            _liability_item(name, u.liability_insurance_expires_on),
        ]:
            if item:
                items.append(item)

        stages = stage_map.get(u.id, {})
        for stage in _STAGES:
            status = stages.get(stage)
            if status and status not in _COMPLETE_STATUSES:
                label = _STAGE_LABELS.get(stage, stage.replace("_", " ").title())
                items.append({"label": f"{name}: Action needed ({label})", "urgency": "action_needed"})

    items.sort(key=lambda x: _URGENCY_RANK.get(x["urgency"], 9))
    return items


async def run_weekly_compliance(db: AsyncSession, dry_run: bool = False) -> dict:
    """Query all billing admins and send compliance summary emails.

    Returns a summary dict: {"sent": int, "skipped": int, "total_admins": int}.
    """
    today = date.today()
    week_of = today.strftime("%B %-d")

    admins_result = await db.execute(
        select(User).where(
            User.role == "billing_admin",
            User.managed_billing_provider_id.isnot(None),
            User.is_active.is_(True),
        )
    )
    admins = admins_result.scalars().all()

    sent = 0
    skipped = 0

    for admin in admins:
        providers_result = await db.execute(
            select(User).where(
                User.billing_provider_id == admin.managed_billing_provider_id,
                User.is_active.is_(True),
            ).order_by(User.full_name)
        )
        providers = providers_result.scalars().all()
        if not providers:
            skipped += 1
            continue

        provider_ids = [p.id for p in providers]
        services_result = await db.execute(
            select(EnrollmentService).where(EnrollmentService.provider_id.in_(provider_ids))
        )
        services = services_result.scalars().all()

        items = _build_items(list(providers), list(services))
        if not items:
            skipped += 1
            continue

        bp_result = await db.execute(
            select(BillingProvider).where(BillingProvider.id == admin.managed_billing_provider_id)
        )
        bp = bp_result.scalar_one_or_none()
        agency_name = bp.name if bp else "Your Agency"

        if not dry_run:
            await email_service.send_weekly_compliance_summary(
                to_email=admin.email,
                to_name=admin.full_name or admin.email.split("@")[0],
                agency_name=agency_name,
                week_of=week_of,
                items=items,
            )

        sent += 1

    return {"sent": sent, "skipped": skipped, "total_admins": len(admins)}


async def _main() -> None:
    dry_run = "--dry-run" in sys.argv
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        result = await run_weekly_compliance(db, dry_run=dry_run)
    await engine.dispose()
    mode = "DRY RUN" if dry_run else "LIVE"
    print(f"[weekly_compliance] {mode} — sent={result['sent']}, skipped={result['skipped']}, total={result['total_admins']}")


if __name__ == "__main__":
    asyncio.run(_main())

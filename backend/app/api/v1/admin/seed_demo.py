"""One-click demo data seed for the Executive Dashboard."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, get_db, require_admin
from app.models.enrollment import EnrollmentService
from app.models.lead import Lead
from app.models.user import User

router = APIRouter(prefix="/admin/seed-demo-data", tags=["admin"])

_GHOST_EMAIL = "demo-ghost-provider@doulashield.internal"


def _ago(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


_DEMO_LEADS: list[dict] = [
    # referral — 8
    {"source": "referral", "status": "converted",      "first_name": "Ashley",    "last_name": "Rivera",      "days_ago": 170},
    {"source": "referral", "status": "converted",      "first_name": "Keisha",    "last_name": "Thompson",    "days_ago": 140},
    {"source": "referral", "status": "converted",      "first_name": "Maria",     "last_name": "Santos",      "days_ago": 100},
    {"source": "referral", "status": "demo_scheduled", "first_name": "Tamara",    "last_name": "Washington",  "days_ago": 30},
    {"source": "referral", "status": "qualified",      "first_name": "Latoya",    "last_name": "Harris",      "days_ago": 45},
    {"source": "referral", "status": "contacted",      "first_name": "Brittany",  "last_name": "Moore",       "days_ago": 60},
    {"source": "referral", "status": "new",            "first_name": "Danielle",  "last_name": "Cooper",      "days_ago": 15},
    {"source": "referral", "status": "not_interested", "first_name": "Imani",     "last_name": "Davis",       "days_ago": 80},
    # facebook — 7
    {"source": "facebook", "status": "converted",      "first_name": "Jennifer",  "last_name": "Williams",    "days_ago": 120},
    {"source": "facebook", "status": "converted",      "first_name": "Serena",    "last_name": "Johnson",     "days_ago": 90},
    {"source": "facebook", "status": "demo_scheduled", "first_name": "Alicia",    "last_name": "Martinez",    "days_ago": 20},
    {"source": "facebook", "status": "qualified",      "first_name": "Nicole",    "last_name": "Brown",       "days_ago": 35},
    {"source": "facebook", "status": "contacted",      "first_name": "Christina", "last_name": "Lee",         "days_ago": 50},
    {"source": "facebook", "status": "new",            "first_name": "Yolanda",   "last_name": "Jackson",     "days_ago": 10},
    {"source": "facebook", "status": "not_interested", "first_name": "Michelle",  "last_name": "White",       "days_ago": 70},
    # website — 5
    {"source": "website",  "status": "converted",      "first_name": "Brianna",   "last_name": "Taylor",      "days_ago": 110},
    {"source": "website",  "status": "converted",      "first_name": "Destiny",   "last_name": "Anderson",    "days_ago": 85},
    {"source": "website",  "status": "qualified",      "first_name": "Victoria",  "last_name": "Thomas",      "days_ago": 40},
    {"source": "website",  "status": "contacted",      "first_name": "Rachel",    "last_name": "Garcia",      "days_ago": 55},
    {"source": "website",  "status": "new",            "first_name": "Stephanie", "last_name": "Martinez",    "days_ago": 25},
    # instagram — 4
    {"source": "instagram","status": "converted",      "first_name": "Jasmine",   "last_name": "Wilson",      "days_ago": 95},
    {"source": "instagram","status": "demo_scheduled", "first_name": "Candace",   "last_name": "Brown",       "days_ago": 18},
    {"source": "instagram","status": "contacted",      "first_name": "Monique",   "last_name": "Davis",       "days_ago": 45},
    {"source": "instagram","status": "new",            "first_name": "Tiffany",   "last_name": "Thompson",    "days_ago": 8},
    # word_of_mouth — 2
    {"source": "word_of_mouth", "status": "converted", "first_name": "Camille",  "last_name": "Roberts",     "days_ago": 130},
    {"source": "word_of_mouth", "status": "new",       "first_name": "Renee",    "last_name": "Mitchell",     "days_ago": 22},
]

_DEMO_SERVICES: list[dict] = [
    # stage, status, created_days_ago, updated_days_ago, pcb_pathway
    {"stage": "pcb",            "status": "complete",    "created": 135, "updated": 100, "pathway": "education_training"},
    {"stage": "pcb",            "status": "complete",    "created": 110, "updated": 80,  "pathway": "experienced"},
    {"stage": "enrollment",     "status": "in_progress", "created": 70,  "updated": 5,   "pathway": None},
    {"stage": "enrollment",     "status": "in_progress", "created": 55,  "updated": 3,   "pathway": None},
    {"stage": "mco_contracting","status": "in_progress", "created": 35,  "updated": 2,   "pathway": None},
    {"stage": "mco_contracting","status": "in_progress", "created": 22,  "updated": 1,   "pathway": None},
    {"stage": "mco_contracting","status": "complete",    "created": 85,  "updated": 60,  "pathway": None},
    {"stage": "pcb",            "status": "in_progress", "created": 12,  "updated": 1,   "pathway": "education_training"},
]


@router.post("")
async def seed_demo_data(
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    # 1. Wipe existing demo leads
    await db.execute(delete(Lead).where(Lead.is_demo == True))  # noqa: E712

    # 2. Insert fresh demo leads
    for ld in _DEMO_LEADS:
        db.add(Lead(
            source=ld["source"],
            status=ld["status"],
            first_name=ld["first_name"],
            last_name=ld["last_name"],
            email=f"{ld['first_name'].lower()}.{ld['last_name'].lower()}@demo.invalid",
            provider_type="doula",
            is_demo=True,
            created_at=_ago(ld["days_ago"]),
        ))

    # 3. Wipe ALL existing demo enrollment services
    await db.execute(delete(EnrollmentService).where(EnrollmentService.is_demo == True))  # noqa: E712

    # 4. Find demo providers; if none exist, use/create a ghost demo provider
    providers_result = await db.execute(
        select(User).where(
            User.role == "provider",
            User.is_demo == True,  # noqa: E712
        )
    )
    demo_providers = list(providers_result.scalars().all())
    ghost_created = False

    if not demo_providers:
        ghost_result = await db.execute(select(User).where(User.email == _GHOST_EMAIL))
        ghost = ghost_result.scalar_one_or_none()
        if ghost is None:
            ghost = User(
                id=uuid.uuid4(),
                email=_GHOST_EMAIL,
                password_hash="!unusable",
                role="provider",
                full_name="DoulaShield Demo Provider",
                is_active=False,
                is_demo=True,
            )
            db.add(ghost)
            await db.flush()
            ghost_created = True
        demo_providers = [ghost]

    # 5. Insert demo enrollment services (round-robin across demo providers)
    for i, svc in enumerate(_DEMO_SERVICES):
        provider = demo_providers[i % len(demo_providers)]
        db.add(EnrollmentService(
            provider_id=provider.id,
            stage=svc["stage"],
            pcb_pathway=svc["pathway"],
            status=svc["status"],
            is_demo=True,
            created_at=_ago(svc["created"]),
            updated_at=_ago(svc["updated"]),
        ))

    await db.commit()

    return {
        "leads_seeded": len(_DEMO_LEADS),
        "enrollment_services_seeded": len(_DEMO_SERVICES),
        "demo_providers_found": len(demo_providers),
        "ghost_provider_created": ghost_created,
    }

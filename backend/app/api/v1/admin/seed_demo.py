"""One-click demo data seed for the Executive Dashboard."""
import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.enrollment import _NPPES_TASKS, _STAGE2_TASKS, _STAGE3_TASKS, _TASK_SEEDS
from app.core.encryption import encrypt_field
from app.core.security import hash_password
from app.dependencies import CurrentUser, get_db, require_admin
from app.models.billing_provider import BillingProvider
from app.models.claim import Claim
from app.models.enrollment import EnrollmentService, EnrollmentTask
from app.models.lead import Lead
from app.models.patient import Patient
from app.models.user import User

router = APIRouter(prefix="/admin/seed-demo-data", tags=["admin"])

_GHOST_EMAIL = "demo-ghost-provider@doulashield.internal"
_BILLING_ADMIN_EMAIL = "demo-billing-admin@doulashield.internal"
_BILLING_ADMIN_PASSWORD = "DoulaShield-Demo-2024!"


def _ago(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def _task_seeds_for(stage: str, pathway: str | None) -> list[dict]:
    if stage == "pcb":
        return _TASK_SEEDS.get(pathway or "education_training", [])
    if stage == "enrollment":
        return _STAGE2_TASKS
    if stage == "mco_contracting":
        return _STAGE3_TASKS
    if stage == "nppes_setup":
        return _NPPES_TASKS
    return []


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

_DEMO_PATIENTS: list[dict] = [
    {"name": "Jasmine Carter",     "medicaid_id": "MA123456789012", "mco": "AmeriHealth Caritas", "days_ago": 90},
    {"name": "Aaliyah Washington", "medicaid_id": "MA234567890123", "mco": "Keystone First",       "days_ago": 75},
    {"name": "Destiny Robinson",   "medicaid_id": "MA345678901234", "mco": "UPMC For You",         "days_ago": 60},
    {"name": "Imani Thompson",     "medicaid_id": "MA456789012345", "mco": "Highmark Wholecare",   "days_ago": 45},
]

_DEMO_CLAIMS: list[dict] = [
    # patient_idx links to _DEMO_PATIENTS above
    {"patient_idx": 0, "payer_id": "23228", "visit_type": "birth",     "billed": 800.00, "paid": None,   "status": "pending_billing_review", "days_ago": 88},
    {"patient_idx": 0, "payer_id": "23228", "visit_type": "prenatal",  "billed": 200.00, "paid": 185.00, "status": "approved",               "days_ago": 91},
    {"patient_idx": 1, "payer_id": "77025", "visit_type": "birth",     "billed": 800.00, "paid": None,   "status": "pending_billing_review", "days_ago": 73},
    {"patient_idx": 1, "payer_id": "77025", "visit_type": "postnatal", "billed": 200.00, "paid": None,   "status": "pending_billing_review", "days_ago": 75},
    {"patient_idx": 2, "payer_id": "88029", "visit_type": "birth",     "billed": 800.00, "paid": 800.00, "status": "approved",               "days_ago": 62},
    {"patient_idx": 3, "payer_id": "58173", "visit_type": "birth",     "billed": 800.00, "paid": None,   "status": "pending_billing_review", "days_ago": 44},
]


@router.post("")
async def seed_demo_data(
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    # ── 1. Demo Leads ─────────────────────────────────────────────────────────
    await db.execute(delete(Lead).where(Lead.is_demo == True))  # noqa: E712
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

    # ── 2. Enrollment Services (wipe + recreate) ──────────────────────────────
    await db.execute(delete(EnrollmentService).where(EnrollmentService.is_demo == True))  # noqa: E712

    # ── 3. Ghost provider (used for enrollment services + billing demo) ────────
    ghost_result = await db.execute(select(User).where(User.email == _GHOST_EMAIL))
    ghost_provider = ghost_result.scalar_one_or_none()
    ghost_created = False
    if ghost_provider is None:
        ghost_provider = User(
            id=uuid.uuid4(),
            email=_GHOST_EMAIL,
            password_hash="!unusable",
            role="provider",
            full_name="DoulaShield Demo Provider",
            is_active=False,
            is_demo=True,
        )
        db.add(ghost_provider)
        await db.flush()
        ghost_created = True

    # For enrollment services: prefer real demo providers; fall back to ghost
    real_demo_result = await db.execute(
        select(User).where(
            User.role == "provider",
            User.is_demo == True,  # noqa: E712
            User.email != _GHOST_EMAIL,
        )
    )
    real_demo_providers = list(real_demo_result.scalars().all())
    enrollment_providers = real_demo_providers if real_demo_providers else [ghost_provider]

    for i, svc in enumerate(_DEMO_SERVICES):
        provider = enrollment_providers[i % len(enrollment_providers)]
        service = EnrollmentService(
            provider_id=provider.id,
            stage=svc["stage"],
            pcb_pathway=svc["pathway"],
            status=svc["status"],
            is_demo=True,
            created_at=_ago(svc["created"]),
            updated_at=_ago(svc["updated"]),
        )
        db.add(service)
        await db.flush()

        task_seeds = _task_seeds_for(svc["stage"], svc["pathway"])
        is_complete = svc["status"] == "complete"
        complete_cutoff = len(task_seeds) if is_complete else math.ceil(len(task_seeds) * 0.6)
        for j, seed in enumerate(task_seeds):
            task_done = j < complete_cutoff
            db.add(EnrollmentTask(
                service_id=service.id,
                task_key=seed["task_key"],
                required_pathway=seed["required_pathway"],
                label=seed["label"],
                description=seed["description"],
                sort_order=seed["sort_order"],
                status="complete" if task_done else "not_started",
                completed_at=_ago(svc["updated"]) if task_done else None,
            ))

    # ── 4. Demo Billing Agency ────────────────────────────────────────────────
    agency_result = await db.execute(
        select(BillingProvider).where(BillingProvider.is_demo == True)  # noqa: E712
    )
    demo_agency = agency_result.scalar_one_or_none()
    if demo_agency is None:
        demo_agency = BillingProvider(
            name="DoulaShield Demo Agency",
            is_demo=True,
            enrollment_tier_enabled=True,
            subscription_status="active",
            group_npi="1234567890",
            address="100 Demo Street",
            city="Philadelphia",
            state="PA",
            zip="19103",
        )
        db.add(demo_agency)
        await db.flush()

    # Assign ghost provider to demo agency so it appears in "My Providers"
    ghost_provider.billing_provider_id = demo_agency.id

    # ── 5. Demo Billing Admin user ────────────────────────────────────────────
    ba_result = await db.execute(select(User).where(User.email == _BILLING_ADMIN_EMAIL))
    billing_admin = ba_result.scalar_one_or_none()
    if billing_admin is None:
        billing_admin = User(
            id=uuid.uuid4(),
            email=_BILLING_ADMIN_EMAIL,
            password_hash=hash_password(_BILLING_ADMIN_PASSWORD),
            role="billing_admin",
            full_name="DoulaShield Demo (Billing Admin)",
            is_active=True,
            is_demo=True,
            managed_billing_provider_id=demo_agency.id,
        )
        db.add(billing_admin)
    else:
        billing_admin.managed_billing_provider_id = demo_agency.id

    await db.flush()

    # ── 6. Demo Patients & Claims (wipe existing for ghost provider first) ────
    await db.execute(delete(Claim).where(Claim.provider_id == ghost_provider.id))
    await db.execute(delete(Patient).where(
        Patient.provider_id == ghost_provider.id,
        Patient.is_demo == True,  # noqa: E712
    ))
    await db.flush()

    demo_patients: list[Patient] = []
    for pd in _DEMO_PATIENTS:
        patient = Patient(
            provider_id=ghost_provider.id,
            name_encrypted=encrypt_field(pd["name"]),
            medicaid_id_encrypted=encrypt_field(pd["medicaid_id"]),
            mco=pd["mco"],
            gender="F",
            is_active=True,
            is_demo=True,
            created_at=_ago(pd["days_ago"]),
        )
        db.add(patient)
        demo_patients.append(patient)
    await db.flush()

    for cd in _DEMO_CLAIMS:
        patient = demo_patients[cd["patient_idx"]]
        db.add(Claim(
            patient_id=patient.id,
            provider_id=ghost_provider.id,
            payer_id=cd["payer_id"],
            visit_type=cd["visit_type"],
            billed_amount=cd["billed"],
            paid_amount=cd["paid"],
            status=cd["status"],
            service_date=_ago(cd["days_ago"]).date(),
            availity_claim_id=f"DEMO-{str(uuid.uuid4())[:8].upper()}",
            is_manual=False,
            created_at=_ago(cd["days_ago"]),
        ))

    await db.commit()

    return {
        "leads_seeded": len(_DEMO_LEADS),
        "enrollment_services_seeded": len(_DEMO_SERVICES),
        "demo_providers_found": len(enrollment_providers),
        "ghost_provider_created": ghost_created,
        "billing_admin_email": _BILLING_ADMIN_EMAIL,
        "patients_seeded": len(_DEMO_PATIENTS),
        "claims_seeded": len(_DEMO_CLAIMS),
    }

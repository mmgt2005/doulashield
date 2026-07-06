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
from app.models.soap_note import SOAPNote
from app.models.user import User
from app.models.visit import Visit

router = APIRouter(prefix="/admin/seed-demo-data", tags=["admin"])

_GHOST_EMAIL = "demo-ghost-provider@doulashield.internal"
_BILLING_ADMIN_EMAIL = "demo-billing-admin@doulashield.internal"
_BILLING_ADMIN_PASSWORD = "DoulaShield-Demo-2024!"
_BA_EMAIL_SUFFIX = "@doulashield.internal"
_BA_EMAIL_PREFIX = "demo-ba-"


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


# Realistic SOAP content keyed by visit_type prefix
_SOAP: dict[str, dict[str, str]] = {
    "labor": {
        "subjective": (
            "Client called at 38 weeks 4 days gestation reporting contractions every 5–7 minutes. "
            "Pain level 6/10. Membranes intact at time of contact. Partner present and supportive."
        ),
        "objective": (
            "Arrived at client's home at 2:15 AM. FHR auscultated at 148 bpm. "
            "Contractions every 4–5 minutes, 60–70 seconds duration, strong intensity. "
            "Client using breathing techniques effectively between contractions."
        ),
        "assessment": (
            "Active labor, progressing well. Client coping effectively with doula support measures "
            "including counter-pressure and positional changes."
        ),
        "plan": (
            "Continuous labor support provided throughout active labor and transition. "
            "Client transferred to hospital at 4:15 AM. Spontaneous vaginal birth at 9:38 AM — "
            "7 lbs 4 oz, APGARs 8/9. Assisted with breastfeeding initiation in the first hour. "
            "Departed at 1:00 PM following postpartum stabilization."
        ),
    },
    "prenatal": {
        "subjective": (
            "Client at 24 weeks gestation. Reports lower back discomfort and difficulty sleeping. "
            "Has questions about birth preferences and pain management options for labor."
        ),
        "objective": (
            "Reviewed and co-developed birth preference document. Demonstrated comfort positioning "
            "for back discomfort relief. Provided printed resource handout on labor positions "
            "and non-pharmacological pain management options."
        ),
        "assessment": (
            "Client well-informed and actively engaged in birth preparation. "
            "Birth preferences clearly documented. No concerns identified."
        ),
        "plan": (
            "Continue prenatal support visits per plan. Review birth preferences at next visit. "
            "Client to schedule hospital tour and confirm support person attendance at next prenatal."
        ),
    },
    "postnatal": {
        "subjective": (
            "Client is 5 days postpartum. Reports breastfeeding challenges — nipple soreness and "
            "concern about milk supply. Infant feeding every 2–3 hours, 15–20 minutes per session."
        ),
        "objective": (
            "Observed breastfeeding — shallow latch noted bilaterally. Provided hands-on support "
            "and repositioning guidance using cross-cradle and football holds. "
            "Client demonstrates improved latch technique by end of visit."
        ),
        "assessment": (
            "Breastfeeding challenge with shallow latch; responding well to corrective positioning. "
            "Milk supply appropriate for day 5 postpartum."
        ),
        "plan": (
            "Follow up in 3 days to assess breastfeeding progress. Provided referral for lactation "
            "consultant. Reviewed normal postpartum recovery milestones and signs to report to OB."
        ),
    },
}


def _soap_for(visit_type: str) -> dict[str, str]:
    if visit_type == "labor":
        return _SOAP["labor"]
    if visit_type.startswith("prenatal"):
        return _SOAP["prenatal"]
    return _SOAP["postnatal"]


# ── Static demo data ─────────────────────────────────────────────────────────

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

# 8 enrollment services spread across stages for the exec dashboard pipeline view.
# These are assigned to real demo providers (or ghost if none exist) — NOT to billing admin providers.
_DEMO_SERVICES: list[dict] = [
    {"stage": "pcb",            "status": "complete",    "created": 135, "updated": 100, "pathway": "education_training"},
    {"stage": "pcb",            "status": "complete",    "created": 110, "updated": 80,  "pathway": "experienced"},
    {"stage": "enrollment",     "status": "in_progress", "created": 70,  "updated": 5,   "pathway": None},
    {"stage": "enrollment",     "status": "in_progress", "created": 55,  "updated": 3,   "pathway": None},
    {"stage": "mco_contracting","status": "in_progress", "created": 35,  "updated": 2,   "pathway": None},
    {"stage": "mco_contracting","status": "in_progress", "created": 22,  "updated": 1,   "pathway": None},
    {"stage": "mco_contracting","status": "complete",    "created": 85,  "updated": 60,  "pathway": None},
    {"stage": "pcb",            "status": "in_progress", "created": 12,  "updated": 1,   "pathway": "education_training"},
]

# 4 dedicated billing admin demo providers — each at a distinct enrollment stage.
# These appear in the billing admin's "My Providers" tab with a clean single-service view.
_BA_DEMO_PROVIDERS: list[dict] = [
    {
        "email": "demo-ba-tamara@doulashield.internal",
        "full_name": "Tamara Williams",
        "stage": "enrollment", "stage_status": "in_progress", "pathway": None,
        "created": 90, "updated": 7,
    },
    {
        "email": "demo-ba-keisha@doulashield.internal",
        "full_name": "Keisha Johnson",
        "stage": "pcb", "stage_status": "in_progress", "pathway": "education_training",
        "created": 35, "updated": 4,
    },
    {
        "email": "demo-ba-maria@doulashield.internal",
        "full_name": "Maria Santos",
        "stage": "mco_contracting", "stage_status": "in_progress", "pathway": None,
        "created": 60, "updated": 3,
    },
    {
        "email": "demo-ba-ashley@doulashield.internal",
        "full_name": "Ashley Thompson",
        "stage": "pcb", "stage_status": "complete", "pathway": "experienced",
        "created": 110, "updated": 75,
    },
]

# Demo patients — provider_idx references _BA_DEMO_PROVIDERS.
# Only providers at enrollment/mco_contracting stages (0=Tamara, 2=Maria) have active patients.
_BA_DEMO_PATIENTS: list[dict] = [
    {"provider_idx": 0, "name": "Destiny Carter",    "medicaid_id": "MA567890123401", "mco": "AmeriHealth Caritas", "payer_id": "23228", "days_ago": 85},
    {"provider_idx": 0, "name": "Brianna Williams",  "medicaid_id": "MA678901234502", "mco": "Keystone First",      "payer_id": "77025", "days_ago": 90},
    {"provider_idx": 2, "name": "Jasmine Robinson",  "medicaid_id": "MA789012345603", "mco": "AmeriHealth Caritas", "payer_id": "23228", "days_ago": 78},
    {"provider_idx": 2, "name": "Aaliyah Thompson",  "medicaid_id": "MA890123456704", "mco": "Keystone First",      "payer_id": "77025", "days_ago": 72},
]

# Demo claims — patient_idx references _BA_DEMO_PATIENTS.
# Rates match PA Medicaid doula fee schedule: labor = $1,000 (T1033), prenatal/postnatal = $100 (T1032).
_BA_DEMO_CLAIMS: list[dict] = [
    # Destiny Carter — Tamara — AmeriHealth
    {"patient_idx": 0, "visit_type": "prenatal_1", "billed": 100.00, "paid": 100.00, "status": "approved",               "days_ago": 80},
    {"patient_idx": 0, "visit_type": "prenatal_2", "billed": 100.00, "paid": None,   "status": "pending_billing_review", "days_ago": 65},
    {"patient_idx": 0, "visit_type": "labor",      "billed": 1000.00,"paid": None,   "status": "pending_billing_review", "days_ago": 44},
    # Brianna Williams — Tamara — Keystone First
    {"patient_idx": 1, "visit_type": "prenatal_1", "billed": 100.00, "paid": 100.00, "status": "approved",               "days_ago": 85},
    {"patient_idx": 1, "visit_type": "labor",      "billed": 1000.00,"paid": None,   "status": "pending_billing_review", "days_ago": 58},
    # Jasmine Robinson — Maria — AmeriHealth
    {"patient_idx": 2, "visit_type": "prenatal_1", "billed": 100.00, "paid": 100.00, "status": "approved",               "days_ago": 74},
    {"patient_idx": 2, "visit_type": "labor",      "billed": 1000.00,"paid": None,   "status": "pending_billing_review", "days_ago": 52},
    {"patient_idx": 2, "visit_type": "postnatal_1","billed": 100.00, "paid": None,   "status": "pending_billing_review", "days_ago": 49},
    # Aaliyah Thompson — Maria — Keystone First
    {"patient_idx": 3, "visit_type": "prenatal_1", "billed": 100.00, "paid": 95.00,  "status": "approved",               "days_ago": 68},
    {"patient_idx": 3, "visit_type": "prenatal_2", "billed": 100.00, "paid": None,   "status": "pending_billing_review", "days_ago": 53},
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

    # ── 2. Enrollment Services (exec dashboard pipeline) — wipe + recreate ────
    await db.execute(delete(EnrollmentService).where(EnrollmentService.is_demo == True))  # noqa: E712

    # ── 3. Ghost provider (used for exec dashboard enrollment services only) ──
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

    # Ensure ghost is NOT assigned to the demo agency (BA demo uses dedicated providers)
    ghost_provider.billing_provider_id = None

    # For exec dashboard enrollment services: prefer real demo providers, fall back to ghost
    real_demo_result = await db.execute(
        select(User).where(
            User.role == "provider",
            User.is_demo == True,  # noqa: E712
            User.email != _GHOST_EMAIL,
            User.email.notlike(f"{_BA_EMAIL_PREFIX}%{_BA_EMAIL_SUFFIX}"),
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

    # ── 5. Billing Admin user ─────────────────────────────────────────────────
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

    # ── 6. Billing admin demo providers (one per enrollment stage) ────────────
    # Wipe and recreate so re-seeds stay clean.
    ba_user_result = await db.execute(
        select(User).where(User.email.like(f"{_BA_EMAIL_PREFIX}%{_BA_EMAIL_SUFFIX}"))
    )
    existing_ba_users = ba_user_result.scalars().all()
    if existing_ba_users:
        ba_ids = [u.id for u in existing_ba_users]
        # Delete in FK-safe order (no DB-level cascade from user → patient/claim/visit)
        await db.execute(delete(Claim).where(Claim.provider_id.in_(ba_ids)))
        patient_result = await db.execute(select(Patient.id).where(Patient.provider_id.in_(ba_ids)))
        ba_patient_ids = [r.id for r in patient_result]
        if ba_patient_ids:
            await db.execute(delete(SOAPNote).where(SOAPNote.patient_id.in_(ba_patient_ids)))
            await db.execute(delete(Visit).where(Visit.patient_id.in_(ba_patient_ids)))
        await db.execute(delete(Patient).where(Patient.provider_id.in_(ba_ids)))
        # EnrollmentService.provider_id has ondelete=CASCADE but bulk delete doesn't trigger it
        await db.execute(delete(EnrollmentService).where(EnrollmentService.provider_id.in_(ba_ids)))
        await db.execute(delete(User).where(User.id.in_(ba_ids)))
        await db.flush()

    # Create fresh billing admin demo providers
    ba_providers: list[User] = []
    for bp_data in _BA_DEMO_PROVIDERS:
        provider = User(
            id=uuid.uuid4(),
            email=bp_data["email"],
            password_hash="!unusable",
            role="provider",
            full_name=bp_data["full_name"],
            is_active=True,
            is_demo=True,
            billing_provider_id=demo_agency.id,
        )
        db.add(provider)
        ba_providers.append(provider)
    await db.flush()

    # One enrollment service per billing admin demo provider
    for idx, (bp_data, provider) in enumerate(zip(_BA_DEMO_PROVIDERS, ba_providers)):
        service = EnrollmentService(
            provider_id=provider.id,
            stage=bp_data["stage"],
            pcb_pathway=bp_data["pathway"],
            status=bp_data["stage_status"],
            is_demo=True,
            created_at=_ago(bp_data["created"]),
            updated_at=_ago(bp_data["updated"]),
        )
        db.add(service)
        await db.flush()

        task_seeds = _task_seeds_for(bp_data["stage"], bp_data["pathway"])
        is_complete = bp_data["stage_status"] == "complete"
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
                completed_at=_ago(bp_data["updated"]) if task_done else None,
            ))

    # ── 7. Demo patients for billing admin providers ───────────────────────────
    ba_patients: list[Patient] = []
    for pd in _BA_DEMO_PATIENTS:
        provider = ba_providers[pd["provider_idx"]]
        patient = Patient(
            provider_id=provider.id,
            name_encrypted=encrypt_field(pd["name"]),
            medicaid_id_encrypted=encrypt_field(pd["medicaid_id"]),
            mco=pd["mco"],
            gender="F",
            is_active=True,
            is_demo=True,
            created_at=_ago(pd["days_ago"]),
        )
        db.add(patient)
        ba_patients.append(patient)
    await db.flush()

    # ── 8. Demo claims + matching visit records with SOAP notes ───────────────
    for cd in _BA_DEMO_CLAIMS:
        patient = ba_patients[cd["patient_idx"]]
        provider = ba_providers[_BA_DEMO_PATIENTS[cd["patient_idx"]]["provider_idx"]]
        payer_id = _BA_DEMO_PATIENTS[cd["patient_idx"]]["payer_id"]
        service_date = _ago(cd["days_ago"]).date()
        soap = _soap_for(cd["visit_type"])

        db.add(Claim(
            patient_id=patient.id,
            provider_id=provider.id,
            payer_id=payer_id,
            visit_type=cd["visit_type"],
            billed_amount=cd["billed"],
            paid_amount=cd["paid"],
            status=cd["status"],
            service_date=service_date,
            availity_claim_id=f"DEMO-{str(uuid.uuid4())[:8].upper()}",
            is_manual=False,
            created_at=_ago(cd["days_ago"]),
        ))

        # Visit record — matched by patient_id + visit_type in the claim review endpoint
        db.add(Visit(
            patient_id=patient.id,
            provider_id=provider.id,
            visit_type=cd["visit_type"],
            visit_date=service_date,
            subjective=soap["subjective"],
            objective=soap["objective"],
            assessment=soap["assessment"],
            plan=soap["plan"],
            location_type="in_person",
            ma91_status="signed",
            ma91_signed_at=_ago(cd["days_ago"] - 1),
        ))

    await db.commit()

    return {
        "leads_seeded": len(_DEMO_LEADS),
        "enrollment_services_seeded": len(_DEMO_SERVICES),
        "demo_providers_found": len(enrollment_providers),
        "ghost_provider_created": ghost_created,
        "billing_admin_email": _BILLING_ADMIN_EMAIL,
        "billing_admin_providers_seeded": len(_BA_DEMO_PROVIDERS),
        "patients_seeded": len(_BA_DEMO_PATIENTS),
        "claims_seeded": len(_BA_DEMO_CLAIMS),
    }

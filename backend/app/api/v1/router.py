from fastapi import APIRouter

from app.api.v1.addresses import router as addresses_router
from app.api.v1.npi import router as npi_router
from app.api.v1.stats import router as stats_router
from app.api.v1.auth import router as auth_router
from app.api.v1.billing import router as billing_router
from app.api.v1.birth_logs import router as birth_logs_router
from app.api.v1.claims import router as claims_router
from app.api.v1.directory import router as directory_router
from app.api.v1.documents import router as documents_router
from app.api.v1.ocr import router as ocr_router
from app.api.v1.patients import router as patients_router
from app.api.v1.prenatal_logs import router as prenatal_logs_router
from app.api.v1.prior_auth import router as prior_auth_router
from app.api.v1.remittances import router as remittances_router
from app.api.v1.signatures import router as signatures_router
from app.api.v1.soap_notes import router as soap_notes_router
from app.api.v1.visits import router as visits_router
from app.api.v1.admin.users import router as admin_users_router
from app.api.v1.admin.audit_logs import router as admin_audit_router
from app.api.v1.admin.billing_providers import router as admin_billing_providers_router
from app.api.v1.admin.executive import router as executive_router
from app.api.v1.admin.seed_demo import router as seed_demo_router
from app.api.v1.enrollment import router as enrollment_router
from app.api.v1.enrollment_billing_admin import router as enrollment_billing_admin_router
from app.api.v1.enrollment_provider import router as enrollment_provider_router
from app.api.v1.public_leads import router as public_leads_router
from app.api.v1.admin_leads import router as admin_leads_router
from app.api.v1.webhooks_cal import router as webhooks_cal_router
from app.api.v1.gmail import router as gmail_router
from app.api.v1.schedule import router as schedule_router

api_router = APIRouter()

api_router.include_router(addresses_router)
api_router.include_router(npi_router)
api_router.include_router(auth_router)
api_router.include_router(billing_router)
api_router.include_router(ocr_router)
api_router.include_router(patients_router)
api_router.include_router(soap_notes_router)
api_router.include_router(prenatal_logs_router)
api_router.include_router(birth_logs_router)
api_router.include_router(visits_router)
api_router.include_router(signatures_router)
api_router.include_router(claims_router)
api_router.include_router(prior_auth_router)
api_router.include_router(remittances_router)
api_router.include_router(documents_router)
api_router.include_router(directory_router)
api_router.include_router(admin_users_router)
api_router.include_router(admin_audit_router)
api_router.include_router(admin_billing_providers_router)
api_router.include_router(executive_router)
api_router.include_router(seed_demo_router)
api_router.include_router(stats_router)
api_router.include_router(enrollment_router)
api_router.include_router(enrollment_billing_admin_router)
api_router.include_router(enrollment_provider_router)
api_router.include_router(public_leads_router)
api_router.include_router(admin_leads_router)
api_router.include_router(webhooks_cal_router)
api_router.include_router(gmail_router)
api_router.include_router(schedule_router)

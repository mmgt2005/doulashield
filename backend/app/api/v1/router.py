from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.birth_logs import router as birth_logs_router
from app.api.v1.patients import router as patients_router
from app.api.v1.prenatal_logs import router as prenatal_logs_router
from app.api.v1.soap_notes import router as soap_notes_router
from app.api.v1.admin.users import router as admin_users_router
from app.api.v1.admin.audit_logs import router as admin_audit_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(patients_router)
api_router.include_router(soap_notes_router)
api_router.include_router(prenatal_logs_router)
api_router.include_router(birth_logs_router)
api_router.include_router(admin_users_router)
api_router.include_router(admin_audit_router)

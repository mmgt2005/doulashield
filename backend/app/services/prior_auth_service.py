from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import AuditLogger
from app.core.encryption import decrypt_field
from app.models.patient import Patient
from app.models.prior_authorization import PriorAuthorization
from app.models.user import User
from app.schemas.prior_auth import PriorAuthCreate, PriorAuthRead
from app.services.availity_client import AvailityClient, MCO_PAYER_IDS

logger = logging.getLogger(__name__)


class PriorAuthService:
    def __init__(self, db: AsyncSession, audit: AuditLogger) -> None:
        self._db = db
        self._audit = audit

    def _make_client(self, user: User) -> AvailityClient:
        if not user.availity_client_id_encrypted or not user.availity_client_secret_encrypted:
            raise ValueError("Provider credentials not configured — connect Availity in Settings")
        return AvailityClient(
            decrypt_field(user.availity_client_id_encrypted),
            decrypt_field(user.availity_client_secret_encrypted),
            str(user.id),
        )

    async def submit_prior_auth(
        self,
        patient_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        data: PriorAuthCreate,
        ip: str,
        user_agent: str,
    ) -> PriorAuthRead:
        user_result = await self._db.execute(select(User).where(User.id == requesting_user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")
        if not user.npi:
            raise ValueError("NPI not configured — add your NPI in Settings")

        patient_result = await self._db.execute(select(Patient).where(Patient.id == patient_id))
        patient = patient_result.scalar_one_or_none()
        if not patient or not patient.is_active:
            raise ValueError("Patient not found")

        payer_id = MCO_PAYER_IDS.get(patient.mco or "")
        if not payer_id:
            raise ValueError("Cannot determine payer — set a recognized MCO on the client profile")

        medicaid_id = decrypt_field(patient.medicaid_id_encrypted)
        name = decrypt_field(patient.name_encrypted)
        name_parts = name.strip().split()
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[-1] if len(name_parts) > 1 else ""

        availity = self._make_client(user)
        now = datetime.now(timezone.utc)

        auth_body: dict = {
            "subscriber": {
                "memberId": medicaid_id,
                "firstName": first_name,
                "lastName": last_name,
            },
            "payer": {"id": payer_id},
            "providers": [{"npi": user.npi}],
            "serviceType": data.service_type,
            "startDate": data.start_date.isoformat(),
            "endDate": data.end_date.isoformat() if data.end_date else None,
            "diagnosisCodes": data.diagnosis_codes,
            "procedureCodes": data.procedure_codes,
        }
        if data.auth_data:
            auth_body.update(data.auth_data)

        raw_response = await availity.post("/prior-authorizations", body=auth_body)

        prior_auth = PriorAuthorization(
            patient_id=patient_id,
            provider_id=requesting_user_id,
            availity_auth_id=raw_response.get("authId") or raw_response.get("id"),
            status=raw_response.get("status", "pending"),
            service_type=data.service_type,
            start_date=data.start_date,
            end_date=data.end_date,
            auth_data=auth_body,
            raw_response=raw_response,
            submitted_at=now,
        )
        self._db.add(prior_auth)
        await self._db.commit()
        await self._db.refresh(prior_auth)

        await self._audit.log(
            action="SUBMIT_PRIOR_AUTH",
            resource_type="prior_authorization",
            resource_id=prior_auth.id,
            ip_address=ip,
            user_agent=user_agent,
            user_id=requesting_user_id,
            extra_context={"patient_id": str(patient_id), "payer_id": payer_id, "service_type": data.service_type},
        )
        return PriorAuthRead.model_validate(prior_auth)

    async def check_auth_status(
        self,
        auth_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        ip: str,
        user_agent: str,
    ) -> PriorAuthRead:
        result = await self._db.execute(
            select(PriorAuthorization).where(
                PriorAuthorization.id == auth_id,
                PriorAuthorization.provider_id == requesting_user_id,
            )
        )
        prior_auth = result.scalar_one_or_none()
        if not prior_auth:
            raise ValueError("Prior authorization not found")
        if not prior_auth.availity_auth_id:
            raise ValueError("Authorization has no Availity ID — it may not have been submitted successfully")

        user_result = await self._db.execute(select(User).where(User.id == requesting_user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        availity = self._make_client(user)
        raw_response = await availity.get(f"/prior-authorizations/{prior_auth.availity_auth_id}")

        prior_auth.status = raw_response.get("status", prior_auth.status)
        prior_auth.end_date = raw_response.get("endDate") or prior_auth.end_date
        prior_auth.raw_response = raw_response
        prior_auth.status_checked_at = datetime.now(timezone.utc)
        await self._db.commit()
        await self._db.refresh(prior_auth)

        await self._audit.log(
            action="CHECK_AUTH_STATUS",
            resource_type="prior_authorization",
            resource_id=auth_id,
            ip_address=ip,
            user_agent=user_agent,
            user_id=requesting_user_id,
            extra_context={"availity_auth_id": prior_auth.availity_auth_id, "status": prior_auth.status},
        )
        return PriorAuthRead.model_validate(prior_auth)

    async def list_prior_auths(
        self,
        requesting_user_id: uuid.UUID,
        patient_id: uuid.UUID,
    ) -> list[PriorAuthRead]:
        result = await self._db.execute(
            select(PriorAuthorization).where(
                PriorAuthorization.provider_id == requesting_user_id,
                PriorAuthorization.patient_id == patient_id,
            ).order_by(PriorAuthorization.created_at.desc())
        )
        return [PriorAuthRead.model_validate(a) for a in result.scalars().all()]

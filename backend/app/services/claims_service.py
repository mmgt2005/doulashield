from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import AuditLogger
from app.core.billing_constants import DOULA_TAXONOMY, PROVIDER_TYPE, billing_for_visit, rate_dollars
from app.core.encryption import decrypt_field
from app.models.claim import Claim
from app.models.patient import Patient
from app.models.user import User
from app.schemas.claim import ClaimCreate, ClaimRead
from app.services.availity_client import AvailityClient, MCO_PAYER_IDS

logger = logging.getLogger(__name__)


class ClaimsService:
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

    async def submit_claim(
        self,
        patient_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        data: ClaimCreate,
        ip: str,
        user_agent: str,
    ) -> ClaimRead:
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

        payer_id = data.payer_id or MCO_PAYER_IDS.get(patient.mco or "")
        if not payer_id:
            raise ValueError("Cannot determine payer — set a recognized MCO on the client profile")

        medicaid_id = decrypt_field(patient.medicaid_id_encrypted)
        name = decrypt_field(patient.name_encrypted)
        name_parts = name.strip().split()
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[-1] if len(name_parts) > 1 else ""

        proc_code, modifier, rate_cents, diag_codes, _ = billing_for_visit(data.visit_type)
        billed_amount = data.billed_amount if data.billed_amount is not None else rate_dollars(data.visit_type)
        diagnosis_codes = data.diagnosis_codes if data.diagnosis_codes else diag_codes
        procedure_codes = data.procedure_codes if data.procedure_codes else [proc_code]
        pos_code = "02" if data.location_type == "telehealth" else "12"

        availity = self._make_client(user)
        now = datetime.now(timezone.utc)

        provider_name_parts = (user.full_name or "").strip().split()
        provider_first = provider_name_parts[0] if provider_name_parts else ""
        provider_last = provider_name_parts[-1] if len(provider_name_parts) > 1 else ""

        claim_body: dict = {
            "subscriber": {
                "memberId": medicaid_id,
                "firstName": first_name,
                "lastName": last_name,
                "gender": patient.gender,
                "birthDate": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            },
            "payer": {"id": payer_id},
            "providers": [{
                "npi": user.npi,
                "taxonomyCode": DOULA_TAXONOMY,
                "providerType": PROVIDER_TYPE,
                "firstName": provider_first,
                "lastName": provider_last,
            }],
            "serviceDate": data.service_date.isoformat(),
            "placeOfService": pos_code,
            "billedAmount": str(billed_amount),
            "diagnosisCodes": diagnosis_codes,
            "procedureCodes": procedure_codes,
            "modifiers": [modifier] if modifier else [],
        }
        if data.claim_data:
            claim_body.update(data.claim_data)

        raw_response = await availity.post("/claims", body=claim_body)

        claim = Claim(
            patient_id=patient_id,
            provider_id=requesting_user_id,
            availity_claim_id=raw_response.get("claimId"),
            status=raw_response.get("status", "submitted"),
            service_date=data.service_date,
            billed_amount=billed_amount,
            payer_id=payer_id,
            claim_data=claim_body,
            raw_response=raw_response,
            submitted_at=now,
        )
        self._db.add(claim)
        await self._db.commit()
        await self._db.refresh(claim)

        await self._audit.log(
            action="SUBMIT_CLAIM",
            resource_type="claim",
            resource_id=claim.id,
            ip_address=ip,
            user_agent=user_agent,
            user_id=requesting_user_id,
            extra_context={"patient_id": str(patient_id), "payer_id": payer_id},
        )
        return ClaimRead.model_validate(claim)

    async def check_claim_status(
        self,
        claim_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        ip: str,
        user_agent: str,
    ) -> ClaimRead:
        claim_result = await self._db.execute(
            select(Claim).where(Claim.id == claim_id, Claim.provider_id == requesting_user_id)
        )
        claim = claim_result.scalar_one_or_none()
        if not claim:
            raise ValueError("Claim not found")
        if not claim.availity_claim_id:
            raise ValueError("Claim has no Availity ID — it may not have been submitted successfully")

        user_result = await self._db.execute(select(User).where(User.id == requesting_user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        availity = self._make_client(user)
        raw_response = await availity.get(f"/claims/{claim.availity_claim_id}/status")

        claim.status = raw_response.get("status", claim.status)
        claim.paid_amount = raw_response.get("paidAmount")
        claim.raw_response = raw_response
        claim.status_checked_at = datetime.now(timezone.utc)
        await self._db.commit()
        await self._db.refresh(claim)

        await self._audit.log(
            action="CHECK_CLAIM_STATUS",
            resource_type="claim",
            resource_id=claim_id,
            ip_address=ip,
            user_agent=user_agent,
            user_id=requesting_user_id,
            extra_context={"availity_claim_id": claim.availity_claim_id, "status": claim.status},
        )
        return ClaimRead.model_validate(claim)

    async def list_claims(
        self,
        requesting_user_id: uuid.UUID,
        patient_id: uuid.UUID,
    ) -> list[ClaimRead]:
        result = await self._db.execute(
            select(Claim).where(
                Claim.provider_id == requesting_user_id,
                Claim.patient_id == patient_id,
            ).order_by(Claim.created_at.desc())
        )
        return [ClaimRead.model_validate(c) for c in result.scalars().all()]

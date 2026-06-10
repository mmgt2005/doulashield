from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import AuditLogger
from app.core.billing_constants import (
    DOULA_TAXONOMY,
    MCO_SUBMISSION_CHANNEL,
    PROVIDER_TYPE,
    billing_for_visit,
    rate_dollars,
)
from app.core.encryption import decrypt_field
from app.models.billing_provider import BillingProvider
from app.models.claim import Claim
from app.models.claim_error_code import ClaimErrorCode
from app.models.patient import Patient
from app.models.user import User
from app.schemas.claim import ClaimCreate, ClaimErrorCodeRead, ClaimRead, ManualClaimUpsert
from app.services.availity_client import AvailityClient, MCO_PAYER_IDS

logger = logging.getLogger(__name__)

# Keyword patterns used to match denial text to a known error code.
# Each entry: (code, list-of-lowercase-keywords — ANY match triggers)
_ERROR_CODE_PATTERNS: list[tuple[str, list[str]]] = [
    ("MOD-U8",    ["modifier", "u8", "u-8", "conflict", "invalid modifier"]),
    ("SIG-MISS",  ["signature", "sig-miss", "unsigned", "missing signature"]),
    ("DT-RANGE",  ["timely filing", "365", "future date", "dt-range", "date of service", "filing limit"]),
    ("DUP-CLAIM", ["duplicate", "dup-claim", "already submitted", "previously submitted", "already exists"]),
]

# Standard X12 adjustment reason code pattern (e.g. "CO-45", "PR-96", "OA-23")
_X12_CODE_RE = re.compile(r'\b([A-Z]{1,3}-\d{1,3})\b')


def _detect_error_code(denial_reason: str) -> str | None:
    """Return the matching known error code, or the first X12 code found, or None."""
    text = denial_reason.lower()
    for code, keywords in _ERROR_CODE_PATTERNS:
        if any(kw in text for kw in keywords):
            return code
    # Fall back to first X12 adjustment code found in the text
    m = _X12_CODE_RE.search(denial_reason)
    return m.group(1) if m else None


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

    async def _apply_error_code(self, claim: Claim, denial_reason: str) -> None:
        """Match denial_reason to an error code and store it on the claim.

        If the detected code isn't in the DB yet, a minimal custom entry is created
        so it will be recognised on future claims.
        """
        code = _detect_error_code(denial_reason)
        if not code:
            return

        existing = await self._db.execute(
            select(ClaimErrorCode).where(ClaimErrorCode.code == code)
        )
        if not existing.scalar_one_or_none():
            # Auto-create a minimal entry for unknown codes so they're searchable later
            new_code = ClaimErrorCode(
                code=code,
                title=f"Denial Code {code}",
                description=denial_reason[:500],
                risk="Review this denial with your billing specialist.",
                fix_instructions="Correct the identified issue and resubmit the claim.",
                is_custom=True,
            )
            self._db.add(new_code)
            await self._db.flush()

        claim.error_code = code

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

        channel = MCO_SUBMISSION_CHANNEL.get(patient.mco or "", "manual")
        if channel == "manual":
            raise ValueError(
                f"Claims for {patient.mco or 'this MCO'} must be submitted manually — "
                "download the CMS 1500 PDF and upload to the correct portal"
            )

        payer_id = data.payer_id or MCO_PAYER_IDS.get(patient.mco or "")
        if not payer_id and channel == "availity":
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

        # Add billing provider when configured — Box 33a / Availity billingProvider
        if user.billing_provider_id:
            bp_result = await self._db.execute(
                select(BillingProvider).where(BillingProvider.id == user.billing_provider_id)
            )
            billing_provider = bp_result.scalar_one_or_none()
            if billing_provider:
                claim_body["billingProvider"] = {
                    "npi": billing_provider.npi,
                    "organizationName": billing_provider.name,
                    "taxonomyCode": billing_provider.taxonomy_code or DOULA_TAXONOMY,
                    "address": {
                        "address1": billing_provider.address or "",
                        "city": billing_provider.city or "",
                        "state": billing_provider.state or "",
                        "postalCode": billing_provider.zip_code or "",
                    },
                }

        client = self._make_client(user)
        raw_response = await client.post("/claims", body=claim_body)

        claim = Claim(
            patient_id=patient_id,
            provider_id=requesting_user_id,
            availity_claim_id=raw_response.get("claimId"),
            visit_type=data.visit_type,
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

    async def resubmit_claim(
        self,
        patient_id: uuid.UUID,
        visit_type: str,
        requesting_user_id: uuid.UUID,
        ip: str,
        user_agent: str,
    ) -> ClaimRead:
        """Re-submit a denied or rejected claim.

        For Availity claims: re-posts the original claim body to Availity and updates
        the existing claim record with the new submission ID.
        For manual claims: resets status to 'submitted' so the provider can log a new outcome.
        """
        user_result = await self._db.execute(select(User).where(User.id == requesting_user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        # Find the most recent claim for this patient + visit slot
        result = await self._db.execute(
            select(Claim).where(
                Claim.patient_id == patient_id,
                Claim.provider_id == requesting_user_id,
                Claim.visit_type == visit_type,
            ).order_by(Claim.created_at.desc())
        )
        claim = result.scalars().first()
        if not claim:
            raise ValueError("No existing claim found for this visit — submit a new claim first")

        now = datetime.now(timezone.utc)

        if claim.is_manual:
            # Manual resubmission: just reset status so provider can track the new submission
            claim.status = "submitted"
            claim.denial_reason = None
            claim.error_code = None
            claim.paid_amount = None
            claim.submitted_at = now
            claim.status_checked_at = now
            claim.resubmit_count = (claim.resubmit_count or 0) + 1
            await self._db.commit()
            await self._db.refresh(claim)
            await self._audit.log(
                action="RESUBMIT_CLAIM",
                resource_type="claim",
                resource_id=claim.id,
                ip_address=ip,
                user_agent=user_agent,
                user_id=requesting_user_id,
                extra_context={"patient_id": str(patient_id), "visit_type": visit_type, "is_manual": True},
            )
            return ClaimRead.model_validate(claim)

        # Availity resubmission: re-post the stored claim body with 837P replacement indicators
        if not claim.claim_data:
            raise ValueError("Original claim data not found — cannot resubmit automatically")

        # Clone payload and inject claim frequency code 7 (replacement) + original claim ID.
        # 837P Loop 2300: CLM05-3 = "7", REF*F8 = original payer claim control number.
        # Availity maps these via claimFrequencyTypeCode and originalClaimId.
        resubmit_body = dict(claim.claim_data)
        resubmit_body["claimFrequencyTypeCode"] = "7"
        if claim.availity_claim_id:
            resubmit_body["originalClaimId"] = claim.availity_claim_id

        client = self._make_client(user)
        raw_response = await client.post("/claims", body=resubmit_body)

        claim.availity_claim_id = raw_response.get("claimId", claim.availity_claim_id)
        claim.status = raw_response.get("status", "submitted")
        claim.denial_reason = None
        claim.error_code = None
        claim.paid_amount = None
        claim.raw_response = raw_response
        claim.submitted_at = now
        claim.status_checked_at = now
        claim.resubmit_count = (claim.resubmit_count or 0) + 1
        await self._db.commit()
        await self._db.refresh(claim)

        await self._audit.log(
            action="RESUBMIT_CLAIM",
            resource_type="claim",
            resource_id=claim.id,
            ip_address=ip,
            user_agent=user_agent,
            user_id=requesting_user_id,
            extra_context={
                "patient_id": str(patient_id),
                "visit_type": visit_type,
                "resubmit_count": claim.resubmit_count,
            },
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
            raise ValueError("Claim has no submission ID — it may not have been submitted successfully")

        user_result = await self._db.execute(select(User).where(User.id == requesting_user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        availity = self._make_client(user)
        raw_response = await availity.get(f"/claims/{claim.availity_claim_id}/status")

        new_status = raw_response.get("status", claim.status)
        claim.status = new_status
        claim.paid_amount = raw_response.get("paidAmount")
        claim.raw_response = raw_response
        claim.status_checked_at = datetime.now(timezone.utc)

        # Auto-match error code when the claim is denied
        denial_reason = raw_response.get("denialReason") or raw_response.get("denial_reason")
        if denial_reason and new_status and new_status.lower() in ("denied", "rejected"):
            claim.denial_reason = denial_reason
            await self._apply_error_code(claim, denial_reason)

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

    async def list_all_provider_claims(
        self,
        requesting_user_id: uuid.UUID,
    ) -> list[ClaimRead]:
        result = await self._db.execute(
            select(Claim).where(
                Claim.provider_id == requesting_user_id,
            ).order_by(Claim.service_date.desc())
        )
        return [ClaimRead.model_validate(c) for c in result.scalars().all()]

    async def list_error_codes(self) -> list[ClaimErrorCodeRead]:
        result = await self._db.execute(select(ClaimErrorCode).order_by(ClaimErrorCode.code))
        return [ClaimErrorCodeRead.model_validate(c) for c in result.scalars().all()]

    async def log_manual_claim(
        self,
        patient_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        visit_type: str,
        data: ManualClaimUpsert,
        ip: str,
        user_agent: str,
    ) -> ClaimRead:
        # Upsert: update existing manual claim for this patient+visit_type if one exists
        existing_result = await self._db.execute(
            select(Claim).where(
                Claim.patient_id == patient_id,
                Claim.provider_id == requesting_user_id,
                Claim.visit_type == visit_type,
                Claim.is_manual.is_(True),
            )
        )
        claim = existing_result.scalar_one_or_none()

        auto_billed = rate_dollars(visit_type)
        now = datetime.now(timezone.utc)
        if claim:
            claim.status = data.status
            claim.service_date = data.service_date
            if data.billed_amount is not None:
                claim.billed_amount = data.billed_amount
            elif claim.billed_amount is None:
                claim.billed_amount = auto_billed
            if data.paid_amount is not None:
                claim.paid_amount = data.paid_amount
            if data.denial_reason is not None:
                claim.denial_reason = data.denial_reason
            claim.status_checked_at = now
        else:
            claim = Claim(
                patient_id=patient_id,
                provider_id=requesting_user_id,
                visit_type=visit_type,
                is_manual=True,
                status=data.status,
                service_date=data.service_date,
                billed_amount=data.billed_amount if data.billed_amount is not None else auto_billed,
                paid_amount=data.paid_amount,
                denial_reason=data.denial_reason,
                submitted_at=now,
            )
            self._db.add(claim)

        # Auto-match error code when denial reason is provided
        if data.denial_reason and data.status == "denied":
            await self._db.flush()  # ensure claim.id exists before applying code
            await self._apply_error_code(claim, data.denial_reason)

        await self._db.commit()
        await self._db.refresh(claim)

        await self._audit.log(
            action="LOG_MANUAL_CLAIM",
            resource_type="claim",
            resource_id=claim.id,
            ip_address=ip,
            user_agent=user_agent,
            user_id=requesting_user_id,
            extra_context={"patient_id": str(patient_id), "visit_type": visit_type, "status": data.status},
        )
        return ClaimRead.model_validate(claim)

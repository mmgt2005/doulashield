from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import AuditLogger
from app.core.encryption import decrypt_field, encrypt_field
from app.models.patient import Patient
from app.models.user import User
from app.schemas.admin import McoContract, ProviderSettingsRead, ProviderSettingsUpdate
from app.services.availity_client import AvailityClient, MCO_PAYER_IDS

logger = logging.getLogger(__name__)


def _parse_mco_contracts(raw: str | None) -> list[McoContract] | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return [McoContract(**item) for item in data] if isinstance(data, list) else None
    except Exception:
        return None


class EligibilityService:
    def __init__(self, db: AsyncSession, audit: AuditLogger) -> None:
        self._db = db
        self._audit = audit

    async def get_provider_settings(self, user_id: uuid.UUID) -> ProviderSettingsRead:
        result = await self._db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")
        admin_q = await self._db.execute(
            select(User).where(User.role == "admin", User.zipzign_api_key_encrypted.isnot(None)).limit(1)
        )
        zipzign_configured = admin_q.scalar_one_or_none() is not None
        today = date.today()
        caqh_expiry = user.caqh_last_attested_on + timedelta(days=90) if user.caqh_last_attested_on else None
        caqh_days_remaining = (caqh_expiry - today).days if caqh_expiry else None
        promise_expiry = user.promise_last_enrolled_on + timedelta(days=1825) if user.promise_last_enrolled_on else None
        promise_days_remaining = (promise_expiry - today).days if promise_expiry else None
        pcb_expiry = user.pcb_last_certified_on + timedelta(days=730) if user.pcb_last_certified_on else None
        pcb_days_remaining = (pcb_expiry - today).days if pcb_expiry else None
        liability_days_remaining = (
            (user.liability_insurance_expires_on - today).days
            if user.liability_insurance_expires_on else None
        )
        return ProviderSettingsRead(
            npi=user.npi,
            availity_connected=bool(user.availity_client_id_encrypted and user.availity_client_secret_encrypted),
            telehealth_link=user.telehealth_link,
            contact_email=user.contact_email,
            zipzign_connected=zipzign_configured,
            zone=user.zone,
            counties=json.loads(user.counties) if user.counties else None,
            provider_address=user.provider_address,
            provider_phone=user.provider_phone,
            provider_ssn_connected=user.provider_ssn_encrypted is not None,
            provider_signature_path=user.provider_signature_path,
            billing_provider_name=user.billing_provider_name,
            mco_contracts=_parse_mco_contracts(user.mco_contracts_json),
            caqh_last_attested_on=user.caqh_last_attested_on,
            caqh_days_remaining=caqh_days_remaining,
            promise_last_enrolled_on=user.promise_last_enrolled_on,
            promise_days_remaining=promise_days_remaining,
            pcb_last_certified_on=user.pcb_last_certified_on,
            pcb_days_remaining=pcb_days_remaining,
            liability_insurance_expires_on=user.liability_insurance_expires_on,
            liability_days_remaining=liability_days_remaining,
        )

    async def update_provider_settings(
        self,
        user_id: uuid.UUID,
        data: ProviderSettingsUpdate,
        ip: str,
        user_agent: str,
    ) -> ProviderSettingsRead:
        result = await self._db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        if data.npi is not None:
            user.npi = data.npi
        if data.availity_client_id is not None:
            user.availity_client_id_encrypted = encrypt_field(data.availity_client_id)
        if data.availity_client_secret is not None:
            user.availity_client_secret_encrypted = encrypt_field(data.availity_client_secret)
        if data.telehealth_link is not None:
            user.telehealth_link = data.telehealth_link
        if data.contact_email is not None:
            user.contact_email = data.contact_email
        if data.zipzign_api_key is not None:
            user.zipzign_api_key_encrypted = None if data.zipzign_api_key == "" else encrypt_field(data.zipzign_api_key)
        if data.zone is not None:
            user.zone = data.zone or None
        if data.counties is not None:
            user.counties = json.dumps(data.counties) if data.counties else None
        if data.provider_address is not None:
            user.provider_address = data.provider_address or None
        if data.provider_phone is not None:
            user.provider_phone = data.provider_phone or None
        if data.provider_ssn is not None:
            user.provider_ssn_encrypted = None if data.provider_ssn == "" else encrypt_field(data.provider_ssn)
        if data.provider_signature_path is not None:
            user.provider_signature_path = data.provider_signature_path or None
        if data.billing_provider_name is not None:
            user.billing_provider_name = data.billing_provider_name or None
        if data.mco_contracts is not None:
            user.mco_contracts_json = (
                json.dumps([c.model_dump(mode="json") for c in data.mco_contracts])
                if data.mco_contracts
                else None
            )
        if data.caqh_last_attested_on is not None:
            user.caqh_last_attested_on = data.caqh_last_attested_on
        if data.promise_last_enrolled_on is not None:
            user.promise_last_enrolled_on = data.promise_last_enrolled_on
        if data.pcb_last_certified_on is not None:
            user.pcb_last_certified_on = data.pcb_last_certified_on
        if data.liability_insurance_expires_on is not None:
            user.liability_insurance_expires_on = data.liability_insurance_expires_on

        await self._db.commit()
        await self._db.refresh(user)

        await self._audit.log(
            action="UPDATE_PROVIDER_SETTINGS",
            resource_type="user",
            resource_id=user_id,
            ip_address=ip,
            user_agent=user_agent,
            user_id=user_id,
        )
        admin_q2 = await self._db.execute(
            select(User).where(User.role == "admin", User.zipzign_api_key_encrypted.isnot(None)).limit(1)
        )
        zipzign_configured = admin_q2.scalar_one_or_none() is not None
        today2 = date.today()
        caqh_expiry2 = user.caqh_last_attested_on + timedelta(days=90) if user.caqh_last_attested_on else None
        caqh_days_remaining2 = (caqh_expiry2 - today2).days if caqh_expiry2 else None
        promise_expiry2 = user.promise_last_enrolled_on + timedelta(days=1825) if user.promise_last_enrolled_on else None
        promise_days_remaining2 = (promise_expiry2 - today2).days if promise_expiry2 else None
        pcb_expiry2 = user.pcb_last_certified_on + timedelta(days=730) if user.pcb_last_certified_on else None
        pcb_days_remaining2 = (pcb_expiry2 - today2).days if pcb_expiry2 else None
        liability_days_remaining2 = (
            (user.liability_insurance_expires_on - today2).days
            if user.liability_insurance_expires_on else None
        )
        return ProviderSettingsRead(
            npi=user.npi,
            availity_connected=bool(user.availity_client_id_encrypted and user.availity_client_secret_encrypted),
            telehealth_link=user.telehealth_link,
            contact_email=user.contact_email,
            zipzign_connected=zipzign_configured,
            zone=user.zone,
            counties=json.loads(user.counties) if user.counties else None,
            provider_address=user.provider_address,
            provider_phone=user.provider_phone,
            provider_ssn_connected=user.provider_ssn_encrypted is not None,
            provider_signature_path=user.provider_signature_path,
            billing_provider_name=user.billing_provider_name,
            mco_contracts=_parse_mco_contracts(user.mco_contracts_json),
            caqh_last_attested_on=user.caqh_last_attested_on,
            caqh_days_remaining=caqh_days_remaining2,
            promise_last_enrolled_on=user.promise_last_enrolled_on,
            promise_days_remaining=promise_days_remaining2,
            pcb_last_certified_on=user.pcb_last_certified_on,
            pcb_days_remaining=pcb_days_remaining2,
            liability_insurance_expires_on=user.liability_insurance_expires_on,
            liability_days_remaining=liability_days_remaining2,
        )

    async def check_eligibility(
        self,
        patient_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        ip: str,
        user_agent: str,
    ) -> dict:
        # Load user credentials
        user_result = await self._db.execute(select(User).where(User.id == requesting_user_id))
        user = user_result.scalar_one_or_none()
        if not user or not user.availity_client_id_encrypted or not user.availity_client_secret_encrypted:
            raise ValueError("Provider credentials not configured — connect Availity in Settings")
        if not user.npi:
            raise ValueError("NPI not configured — add your NPI in Settings")

        # Load patient
        patient_result = await self._db.execute(select(Patient).where(Patient.id == patient_id))
        patient = patient_result.scalar_one_or_none()
        if not patient or not patient.is_active:
            raise ValueError("Patient not found")

        if not patient.date_of_birth:
            raise ValueError("Date of birth required — add it to the client profile first")

        mco = patient.mco or "FFS"
        payer_id = MCO_PAYER_IDS.get(mco)
        if not payer_id:
            raise ValueError(f"MCO '{mco}' is not recognized — update the client's MCO")

        medicaid_id = decrypt_field(patient.medicaid_id_encrypted)
        name = decrypt_field(patient.name_encrypted)
        name_parts = name.strip().split()
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[-1] if len(name_parts) > 1 else ""

        client_id = decrypt_field(user.availity_client_id_encrypted)
        client_secret = decrypt_field(user.availity_client_secret_encrypted)
        availity = AvailityClient(client_id, client_secret, str(requesting_user_id))

        coverage = await availity.post(
            "/coverages",
            body={
                "subscriber": {
                    "memberId": medicaid_id,
                    "firstName": first_name,
                    "lastName": last_name,
                    "birthDate": patient.date_of_birth.isoformat(),
                },
                "payer": {"id": payer_id},
                "providers": [{"npi": user.npi}],
                "serviceType": ["30"],
            },
        )

        active = coverage.get("subscriberStatus", "").lower() == "active"
        plan_name = coverage.get("planDescription") or mco
        effective_date = coverage.get("effectiveDate")

        now = datetime.now(timezone.utc)
        patient.eligibility_status = "active" if active else "inactive"
        patient.eligibility_checked_at = now
        await self._db.commit()

        await self._audit.log(
            action="CHECK_ELIGIBILITY",
            resource_type="patient",
            resource_id=patient_id,
            ip_address=ip,
            user_agent=user_agent,
            user_id=requesting_user_id,
            extra_context={"mco": mco, "active": active},
        )

        return {
            "active": active,
            "plan_name": plan_name,
            "effective_date": effective_date,
            "checked_at": now.isoformat(),
        }

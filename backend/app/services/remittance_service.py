from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import AuditLogger
from app.core.encryption import decrypt_field
from app.models.claim import Claim
from app.models.remittance import Remittance
from app.models.user import User
from app.schemas.remittance import RemittanceFetchRequest, RemittanceRead
from app.services.availity_client import AvailityClient
from app.services.stripe_service import process_escrow_deduction

logger = logging.getLogger(__name__)

# ── Availity 835 claim status → our normalized status strings ──────────────────
_STATUS_MAP: dict[str, str] = {
    # Numeric 835 codes
    "1": "paid", "2": "denied", "3": "denied", "4": "processing",
    "19": "processing", "20": "denied", "22": "processing",
    # String variants from Availity
    "paid": "paid", "approved": "paid", "p": "paid",
    "finalized/payment": "paid", "finalized - payment": "paid",
    "denied": "denied", "d": "denied", "rejected": "denied", "r": "denied",
    "processing": "processing", "pended": "processing",
    "received": "processing", "accepted": "processing",
    "partial": "processing", "partially paid": "processing",
}

# Common X12 835 adjustment reason code descriptions (PA Medicaid focus)
_REASON_DESCRIPTIONS: dict[str, str] = {
    "CO-4": "Service/procedure code inconsistent with the modifier",
    "CO-11": "Diagnosis inconsistent with the procedure",
    "CO-15": "Authorization number missing, invalid, or does not apply",
    "CO-16": "Claim/service lacks information needed for adjudication",
    "CO-18": "Duplicate claim/service",
    "CO-22": "This care may be covered by another payer",
    "CO-45": "Charge exceeds fee schedule/maximum allowable",
    "CO-55": "Procedure/service not appropriate for the patient's age",
    "CO-56": "Procedure/service not appropriate for the patient's sex",
    "CO-97": "Benefit for this service included in the payment for another service",
    "CO-109": "Claim not covered by this payer; forward to the correct payer",
    "CO-119": "Benefit maximum for this time period has been reached",
    "CO-167": "This service was not prescribed by a qualified provider",
    "CO-197": "Precertification/authorization not obtained",
    "PR-1": "Deductible amount",
    "PR-2": "Coinsurance amount",
    "PR-3": "Co-payment amount",
    "PR-96": "Non-covered charge(s)",
    "OA-23": "Payment adjusted due to prior payment",
    "OA-94": "Processed in excess of charges",
    "N30": "Patient ineligible for the date of service",
}


def _normalize_status(raw: str | None) -> str | None:
    if not raw:
        return None
    return _STATUS_MAP.get(str(raw).strip().lower())


def _format_denial_reason(adjustments: list[dict]) -> str | None:
    """Build a human-readable denial reason string from X12 835 adjustment records."""
    if not adjustments:
        return None
    parts: list[str] = []
    for adj in adjustments:
        group = (adj.get("adjustmentGroupCode") or adj.get("groupCode") or "").strip().upper()
        code = (adj.get("adjustmentReasonCode") or adj.get("reasonCode") or "").strip()
        desc = (
            adj.get("adjustmentReasonDescription")
            or adj.get("reasonDescription")
            or adj.get("description")
            or ""
        ).strip()
        if not group or not code:
            continue
        key = f"{group}-{code}"
        if not desc:
            desc = _REASON_DESCRIPTIONS.get(key, "")
        parts.append(f"{key}: {desc}" if desc else key)
    return "; ".join(parts) if parts else None


def _extract_claim_lines(raw: dict) -> list[dict]:
    """Defensively extract claimPayments from various Availity 835 response shapes."""
    if not raw:
        return []
    # Shape A: direct claimPayments key
    lines = raw.get("claimPayments")
    if isinstance(lines, list) and lines:
        return lines
    # Shape B: nested under financialInformation
    fi = raw.get("financialInformation") or {}
    lines = fi.get("claimPayments")
    if isinstance(lines, list) and lines:
        return lines
    # Shape C: "claims" key (older API versions)
    lines = raw.get("claims")
    if isinstance(lines, list) and lines:
        return lines
    # Shape D: "serviceLines" fallback
    lines = raw.get("serviceLines")
    if isinstance(lines, list) and lines:
        return lines
    return []


class RemittanceService:
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

    async def _update_claims_from_remittance(
        self,
        remittance: Remittance,
        provider_id: uuid.UUID,
    ) -> int:
        """
        Parse claim payment lines from a saved remittance and update matching Claim rows.
        Returns the number of claims updated.
        """
        raw = remittance.raw_response or {}
        claim_lines = _extract_claim_lines(raw)

        if not claim_lines:
            logger.debug(
                "remittance %s: no claim payment lines found; raw keys=%s",
                remittance.id,
                list(raw.keys()),
            )
            return 0

        updated = 0
        now = datetime.now(timezone.utc)

        for line in claim_lines:
            # Availity uses several field names for the submission control number
            ccn = (
                line.get("claimControlNumber")
                or line.get("claimReferenceNumber")
                or line.get("claimId")
                or line.get("referenceNumber")
                or line.get("internalControlNumber")
            )
            if not ccn:
                logger.debug(
                    "remittance %s: claim line missing control number; keys=%s",
                    remittance.id,
                    list(line.keys()),
                )
                continue

            # Paid amount — may be zero for full denials
            paid_raw = (
                line.get("claimPaymentAmount")
                or line.get("paymentAmount")
                or line.get("paidAmount")
            )
            paid_amount: Decimal | None = None
            if paid_raw is not None:
                try:
                    paid_amount = Decimal(str(paid_raw))
                except Exception:
                    pass

            # Status — explicit field, then infer from paid amount
            raw_status = (
                line.get("claimStatusCode")
                or line.get("claimStatus")
                or line.get("status")
                or line.get("statusCode")
            )
            normalized_status = _normalize_status(raw_status)
            if normalized_status is None and paid_amount is not None:
                normalized_status = "paid" if paid_amount > 0 else "denied"

            # Build denial reason from adjustment codes
            adjustments = line.get("claimAdjustments") or line.get("adjustments") or []
            denial_reason = _format_denial_reason(adjustments) if isinstance(adjustments, list) else None

            result = await self._db.execute(
                select(Claim).where(
                    Claim.availity_claim_id == str(ccn),
                    Claim.provider_id == provider_id,
                )
            )
            claim = result.scalar_one_or_none()
            if not claim:
                logger.debug(
                    "remittance %s: no claim found for availity_claim_id=%s",
                    remittance.id,
                    ccn,
                )
                continue

            changed = False
            if normalized_status and normalized_status != claim.status:
                claim.status = normalized_status
                changed = True
            if paid_amount is not None and paid_amount != claim.paid_amount:
                claim.paid_amount = paid_amount
                changed = True
            if denial_reason and denial_reason != claim.denial_reason:
                claim.denial_reason = denial_reason
                changed = True
            if claim.remittance_id != remittance.id:
                claim.remittance_id = remittance.id
                changed = True

            if changed:
                claim.status_checked_at = now
                updated += 1
                logger.info(
                    "remittance %s: updated claim %s (availity_id=%s) status=%s paid=%s",
                    remittance.id,
                    claim.id,
                    ccn,
                    claim.status,
                    claim.paid_amount,
                )

        if updated > 0:
            await self._db.commit()

        return updated

    async def fetch_remittances(
        self,
        requesting_user_id: uuid.UUID,
        data: RemittanceFetchRequest,
        ip: str,
        user_agent: str,
    ) -> list[RemittanceRead]:
        user_result = await self._db.execute(select(User).where(User.id == requesting_user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")
        if not user.npi:
            raise ValueError("NPI not configured — add your NPI in Settings")

        availity = self._make_client(user)
        params: dict = {
            "npi": user.npi,
            "startDate": data.start_date.isoformat(),
            "endDate": data.end_date.isoformat(),
        }
        if data.payer_id:
            params["payerId"] = data.payer_id

        raw = await availity.get("/remittances", params=params)

        remit_list = raw if isinstance(raw, list) else raw.get("remittances", [])
        saved: list[RemittanceRead] = []

        for item in remit_list:
            remit_id = item.get("remittanceId") or item.get("id")
            existing = None
            if remit_id:
                existing_result = await self._db.execute(
                    select(Remittance).where(Remittance.availity_remit_id == remit_id)
                )
                existing = existing_result.scalar_one_or_none()

            if existing:
                existing.raw_response = item
                await self._db.commit()
                await self._db.refresh(existing)
                saved.append(RemittanceRead.model_validate(existing))
                # Re-parse even for existing remittances — payer may have issued late adjustments
                await self._update_claims_from_remittance(existing, requesting_user_id)
            else:
                payment_date_raw = item.get("paymentDate")
                payment_date: date | None = None
                if payment_date_raw:
                    try:
                        payment_date = date.fromisoformat(payment_date_raw)
                    except ValueError:
                        pass

                remittance = Remittance(
                    provider_id=requesting_user_id,
                    availity_remit_id=remit_id,
                    check_number=item.get("checkNumber"),
                    payer_id=item.get("payerId"),
                    payment_date=payment_date,
                    total_payment=item.get("totalPayment"),
                    raw_response=item,
                )
                self._db.add(remittance)
                await self._db.commit()
                await self._db.refresh(remittance)
                saved.append(RemittanceRead.model_validate(remittance))

                if remittance.total_payment and remittance.total_payment > 0:
                    await process_escrow_deduction(
                        user,
                        Decimal(str(remittance.total_payment)),
                        remittance.id,
                        self._db,
                    )

                await self._update_claims_from_remittance(remittance, requesting_user_id)

        await self._audit.log(
            action="FETCH_REMITTANCES",
            resource_type="remittance",
            ip_address=ip,
            user_agent=user_agent,
            user_id=requesting_user_id,
            extra_context={
                "start_date": data.start_date.isoformat(),
                "end_date": data.end_date.isoformat(),
                "count": len(saved),
            },
        )
        return saved

    async def list_remittances(
        self,
        requesting_user_id: uuid.UUID,
    ) -> list[RemittanceRead]:
        result = await self._db.execute(
            select(Remittance)
            .where(Remittance.provider_id == requesting_user_id)
            .order_by(Remittance.payment_date.desc())
        )
        return [RemittanceRead.model_validate(r) for r in result.scalars().all()]

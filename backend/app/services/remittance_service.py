from __future__ import annotations

import logging
import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import AuditLogger
from app.core.encryption import decrypt_field
from app.models.remittance import Remittance
from app.models.user import User
from app.schemas.remittance import RemittanceFetchRequest, RemittanceRead
from app.services.availity_client import AvailityClient
from app.services.stripe_service import process_escrow_deduction

logger = logging.getLogger(__name__)


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
                    from decimal import Decimal
                    await process_escrow_deduction(
                        user,
                        Decimal(str(remittance.total_payment)),
                        remittance.id,
                        self._db,
                    )

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

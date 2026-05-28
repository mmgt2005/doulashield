from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import AuditLogger
from app.core.encryption import decrypt_field
from app.models.user import User
from app.schemas.directory import DirectoryProvider, DirectorySearchResponse
from app.services.availity_client import AvailityClient

logger = logging.getLogger(__name__)


class DirectoryService:
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

    async def search_providers(
        self,
        requesting_user_id: uuid.UUID,
        query_params: dict,
        ip: str,
        user_agent: str,
    ) -> DirectorySearchResponse:
        user_result = await self._db.execute(select(User).where(User.id == requesting_user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        availity = self._make_client(user)
        raw = await availity.get("/directory", params=query_params)

        provider_list = raw if isinstance(raw, list) else raw.get("providers", [])
        providers = [
            DirectoryProvider(
                npi=p.get("npi"),
                name=p.get("name") or p.get("fullName"),
                specialty=p.get("specialty") or p.get("primarySpecialty"),
                address=p.get("address") or p.get("primaryAddress"),
                phone=p.get("phone") or p.get("primaryPhone"),
            )
            for p in provider_list
        ]

        await self._audit.log(
            action="DIRECTORY_SEARCH",
            resource_type="directory",
            ip_address=ip,
            user_agent=user_agent,
            user_id=requesting_user_id,
            extra_context={**query_params, "result_count": len(providers)},
        )
        return DirectorySearchResponse(providers=providers, total=len(providers))

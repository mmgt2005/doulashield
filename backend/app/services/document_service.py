from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import AuditLogger
from app.core.encryption import decrypt_field
from app.models.user import User
from app.schemas.document import DocumentSubmitResponse
from app.services.availity_client import AvailityClient

logger = logging.getLogger(__name__)


class DocumentService:
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

    async def submit_document(
        self,
        requesting_user_id: uuid.UUID,
        file_bytes: bytes,
        content_type: str,
        filename: str,
        metadata: dict,
        ip: str,
        user_agent: str,
    ) -> DocumentSubmitResponse:
        user_result = await self._db.execute(select(User).where(User.id == requesting_user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")
        if not user.npi:
            raise ValueError("NPI not configured — add your NPI in Settings")

        availity = self._make_client(user)
        raw_response = await availity.post_multipart(
            "/documents",
            files={"file": (filename, file_bytes, content_type)},
            data={"npi": user.npi, **{k: str(v) for k, v in metadata.items()}},
        )

        doc_id = raw_response.get("documentId") or raw_response.get("id", "")
        status = raw_response.get("status", "submitted")

        await self._audit.log(
            action="SUBMIT_DOCUMENT",
            resource_type="document",
            ip_address=ip,
            user_agent=user_agent,
            user_id=requesting_user_id,
            extra_context={
                "availity_document_id": doc_id,
                "content_type": content_type,
                **{k: str(v) for k, v in metadata.items()},
            },
        )
        return DocumentSubmitResponse(availity_document_id=doc_id, status=status)

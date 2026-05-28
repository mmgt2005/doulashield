from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditLogger
from app.dependencies import CurrentUser, get_audit, get_client_ip, get_current_user, get_db, get_user_agent
from app.schemas.document import DocumentSubmitResponse
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])

_ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png", "text/xml", "application/xml"}
_MAX_SIZE = 10 * 1024 * 1024  # 10 MB


def _svc(db: AsyncSession, audit: AuditLogger) -> DocumentService:
    return DocumentService(db, audit)


@router.post("/submit", response_model=DocumentSubmitResponse, status_code=status.HTTP_201_CREATED)
async def submit_document(
    request: Request,
    file: Annotated[UploadFile, File()],
    claim_id: Annotated[str | None, Form()] = None,
    auth_id: Annotated[str | None, Form()] = None,
    document_type: Annotated[str, Form()] = "clinical_note",
    current_user: Annotated[CurrentUser, Depends(get_current_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
    audit: Annotated[AuditLogger, Depends(get_audit)] = ...,
) -> DocumentSubmitResponse:
    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported file type")

    file_bytes = await file.read()
    if len(file_bytes) > _MAX_SIZE:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="File exceeds 10 MB limit")

    metadata: dict = {"documentType": document_type}
    if claim_id:
        metadata["claimId"] = claim_id
    if auth_id:
        metadata["authId"] = auth_id

    try:
        return await _svc(db, audit).submit_document(
            current_user.id,
            file_bytes,
            file.content_type or "application/octet-stream",
            file.filename or "document",
            metadata,
            get_client_ip(request),
            get_user_agent(request),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

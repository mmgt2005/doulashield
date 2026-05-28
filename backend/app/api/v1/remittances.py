from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditLogger
from app.dependencies import CurrentUser, get_audit, get_client_ip, get_current_user, get_db, get_user_agent
from app.schemas.remittance import RemittanceFetchRequest, RemittanceRead
from app.services.remittance_service import RemittanceService

router = APIRouter(prefix="/remittances", tags=["remittances"])


def _svc(db: AsyncSession, audit: AuditLogger) -> RemittanceService:
    return RemittanceService(db, audit)


@router.post("/fetch", response_model=list[RemittanceRead])
async def fetch_remittances(
    request: Request,
    body: RemittanceFetchRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> list[RemittanceRead]:
    try:
        return await _svc(db, audit).fetch_remittances(
            current_user.id, body, get_client_ip(request), get_user_agent(request)
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=list[RemittanceRead])
async def list_remittances(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> list[RemittanceRead]:
    return await _svc(db, audit).list_remittances(current_user.id)

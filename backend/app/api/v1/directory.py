from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditLogger
from app.dependencies import CurrentUser, get_audit, get_client_ip, get_current_user, get_db, get_user_agent
from app.schemas.directory import DirectorySearchResponse
from app.services.directory_service import DirectoryService

router = APIRouter(prefix="/directory", tags=["directory"])


def _svc(db: AsyncSession, audit: AuditLogger) -> DirectoryService:
    return DirectoryService(db, audit)


@router.get("/search", response_model=DirectorySearchResponse)
async def search_providers(
    request: Request,
    npi: Annotated[str | None, Query(description="Provider NPI")] = None,
    name: Annotated[str | None, Query(description="Provider name")] = None,
    specialty: Annotated[str | None, Query(description="Specialty or taxonomy code")] = None,
    payer_id: Annotated[str | None, Query(description="Availity payer ID to filter network")] = None,
    zip_code: Annotated[str | None, Query(description="ZIP code for proximity search")] = None,
    current_user: Annotated[CurrentUser, Depends(get_current_user)] = ...,
    db: Annotated[AsyncSession, Depends(get_db)] = ...,
    audit: Annotated[AuditLogger, Depends(get_audit)] = ...,
) -> DirectorySearchResponse:
    query_params = {k: v for k, v in {
        "npi": npi,
        "name": name,
        "specialty": specialty,
        "payerId": payer_id,
        "zipCode": zip_code,
    }.items() if v is not None}

    if not query_params:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one search parameter is required",
        )

    try:
        return await _svc(db, audit).search_providers(
            current_user.id, query_params, get_client_ip(request), get_user_agent(request)
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

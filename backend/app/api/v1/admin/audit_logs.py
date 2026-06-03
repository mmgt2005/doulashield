import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, get_db, require_admin
from app.schemas.admin import AuditLogRead
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin/audit-logs", tags=["admin"])


@router.get("", response_model=list[AuditLogRead])
async def list_audit_logs(
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    resource_type: str | None = Query(default=None),
    user_id: uuid.UUID | None = Query(default=None),
    action: str | None = Query(default=None),
    user_email: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[AuditLogRead]:
    return await AdminService(db).list_audit_logs(
        resource_type=resource_type,
        user_id=user_id,
        action=action,
        user_email=user_email,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )

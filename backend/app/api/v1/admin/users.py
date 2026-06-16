import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import AuditLogger
from app.core.security import create_access_token
from app.dependencies import CurrentUser, get_audit, get_client_ip, get_db, get_user_agent, require_admin
from app.models.user import User
from app.schemas.admin import UserCreate, UserRead, UserUpdate
from app.schemas.auth import ImpersonateResponse
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin/users", tags=["admin"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserRead:
    try:
        return await AdminService(db).create_user(body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=list[UserRead])
async def list_users(
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[UserRead]:
    return await AdminService(db).list_users()


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    _: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserRead:
    try:
        return await AdminService(db).update_user(user_id, body)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.post("/{user_id}/impersonate", response_model=ImpersonateResponse)
async def impersonate_user(
    request: Request,
    user_id: uuid.UUID,
    admin: Annotated[CurrentUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> ImpersonateResponse:
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()

    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.role == "billing_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot impersonate billing admin accounts")
    if target.id == admin.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot impersonate yourself")

    imp_token = create_access_token(
        str(target.id),
        target.role,
        extra={"imp": str(admin.id)},
    )

    await audit.log(
        action="IMPERSONATE_START",
        resource_type="user",
        resource_id=target.id,
        user_id=admin.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        extra_context={
            "admin_id": str(admin.id),
            "target_id": str(target.id),
            "target_email": target.email,
        },
    )

    return ImpersonateResponse(
        access_token=imp_token,
        target_id=str(target.id),
        target_email=target.email,
        target_name=target.full_name,
    )

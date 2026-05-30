from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.security import hash_password, is_valid_password
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.admin import AuditLogRead, UserCreate, UserRead, UserUpdate


class AdminService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_user(self, data: UserCreate) -> UserRead:
        if not is_valid_password(data.password):
            raise ValueError(
                "Password must be at least 12 characters and include uppercase, lowercase, "
                "digit, and special character."
            )

        user = User(
            id=uuid.uuid4(),
            email=data.email,
            password_hash=hash_password(data.password),  # type: ignore[call-arg]
            role=data.role,
            full_name=data.full_name,
        )
        if data.role == "admin":
            user.deposit_paid = True
            user.escrow_balance_remaining = Decimal("0.00")
        self._db.add(user)
        await self._db.commit()
        await self._db.refresh(user)
        return UserRead.model_validate(user)

    async def list_users(self) -> list[UserRead]:
        result = await self._db.execute(select(User))
        return [UserRead.model_validate(u) for u in result.scalars().all()]

    async def update_user(self, user_id: uuid.UUID, data: UserUpdate) -> UserRead:
        result = await self._db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)

        await self._db.commit()
        await self._db.refresh(user)
        return UserRead.model_validate(user)

    async def list_audit_logs(
        self,
        resource_type: str | None = None,
        user_id: uuid.UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLogRead]:
        query = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        if user_id:
            query = query.where(AuditLog.user_id == user_id)

        result = await self._db.execute(query)
        return [AuditLogRead.model_validate(r) for r in result.scalars().all()]

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from supabase._async.client import AsyncClient


class AuditLogger:
    """Insert-only audit trail. Never call update or delete on audit_logs."""

    def __init__(self, db: "AsyncClient") -> None:
        self._db = db

    async def log(
        self,
        action: str,
        ip_address: str,
        user_agent: str,
        user_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: uuid.UUID | None = None,
        extra_context: dict | None = None,
    ) -> None:
        await self._db.table("audit_logs").insert(
            {
                "user_id": str(user_id) if user_id else None,
                "action": action,
                "resource_type": resource_type,
                "resource_id": str(resource_id) if resource_id else None,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "extra_context": extra_context or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()

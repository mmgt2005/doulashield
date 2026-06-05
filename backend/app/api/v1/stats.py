from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User

router = APIRouter(tags=["stats"])

_STATUS_MAP = {
    "paid": "paid",
    "approved": "paid",
    "denied": "denied",
    "rejected": "denied",
    "processing": "processing",
    "accepted": "processing",
    "pended": "processing",
    "received": "processing",
}


def _normalize_status(raw: str | None) -> str:
    if not raw:
        return "submitted"
    return _STATUS_MAP.get(raw.lower(), "submitted")


@router.get("/stats/summary")
async def get_stats_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    uid = str(current_user.id)

    patient_row = await db.execute(
        text(
            "SELECT COUNT(*) FROM public.patients WHERE provider_id = :uid AND is_active = true"
        ),
        {"uid": uid},
    )
    total_patients = patient_row.scalar() or 0

    visit_row = await db.execute(
        text(
            """
            SELECT
              COUNT(*) FILTER (WHERE visit_ended_at IS NOT NULL) AS completed,
              COUNT(*) AS documented
            FROM public.visits WHERE provider_id = :uid
            """
        ),
        {"uid": uid},
    )
    vrow = visit_row.fetchone()
    visits_completed = int(vrow.completed) if vrow else 0
    visits_documented = int(vrow.documented) if vrow else 0

    claims_rows = await db.execute(
        text(
            """
            SELECT status,
                   COUNT(*) AS cnt,
                   COALESCE(SUM(billed_amount), 0) AS billed,
                   COALESCE(SUM(paid_amount), 0) AS paid
            FROM public.claims WHERE provider_id = :uid
            GROUP BY status
            """
        ),
        {"uid": uid},
    )

    buckets: dict[str, dict] = {
        "submitted":  {"count": 0, "billed": 0.0},
        "processing": {"count": 0, "billed": 0.0},
        "paid":       {"count": 0, "billed": 0.0, "paid": 0.0},
        "denied":     {"count": 0, "billed": 0.0},
    }
    total_billed = 0.0
    total_paid = 0.0

    for row in claims_rows.fetchall():
        bucket = _normalize_status(row.status)
        count = int(row.cnt)
        billed = float(row.billed)
        paid = float(row.paid)
        buckets[bucket]["count"] += count
        buckets[bucket]["billed"] += billed
        if bucket == "paid":
            buckets[bucket]["paid"] = buckets[bucket].get("paid", 0.0) + paid
        total_billed += billed
        total_paid += paid

    mco_rows = await db.execute(
        text(
            """
            SELECT p.mco,
                   COUNT(DISTINCT c.patient_id) AS patients,
                   COUNT(c.id) AS claims,
                   COALESCE(SUM(c.billed_amount), 0) AS billed,
                   COALESCE(SUM(c.paid_amount), 0) AS paid
            FROM public.claims c
            JOIN public.patients p ON c.patient_id = p.id
            WHERE c.provider_id = :uid
            GROUP BY p.mco
            """
        ),
        {"uid": uid},
    )

    mco_breakdown = [
        {
            "mco": row.mco,
            "patients": int(row.patients),
            "claims": int(row.claims),
            "billed": float(row.billed),
            "paid": float(row.paid),
        }
        for row in mco_rows.fetchall()
    ]

    deadline_rows = await db.execute(
        text(
            """
            SELECT
              COUNT(*) FILTER (
                WHERE submitted_at IS NULL
                  AND (status IS NULL OR status NOT IN ('paid'))
                  AND service_date IS NOT NULL
                  AND service_date + INTERVAL '180 days' < CURRENT_DATE
              ) AS overdue_count,
              COUNT(*) FILTER (
                WHERE submitted_at IS NULL
                  AND (status IS NULL OR status NOT IN ('paid'))
                  AND service_date IS NOT NULL
                  AND service_date + INTERVAL '150 days' < CURRENT_DATE
                  AND service_date + INTERVAL '180 days' >= CURRENT_DATE
              ) AS urgent_count,
              COUNT(*) FILTER (
                WHERE submitted_at IS NULL
                  AND (status IS NULL OR status NOT IN ('paid'))
                  AND service_date IS NOT NULL
                  AND service_date + INTERVAL '30 days' < CURRENT_DATE
              ) AS unfiled_past_30_days
            FROM public.claims WHERE provider_id = :uid
            """
        ),
        {"uid": uid},
    )
    drow = deadline_rows.fetchone()
    claim_deadline_summary = {
        "overdue_count": int(drow.overdue_count) if drow else 0,
        "urgent_count": int(drow.urgent_count) if drow else 0,
        "unfiled_past_30_days": int(drow.unfiled_past_30_days) if drow else 0,
    }

    return {
        "total_patients": int(total_patients),
        "visits_completed": visits_completed,
        "visits_documented": visits_documented,
        "claims": buckets,
        "revenue": {
            "total_billed": total_billed,
            "total_paid": total_paid,
        },
        "mco_breakdown": mco_breakdown,
        "claim_deadline_summary": claim_deadline_summary,
    }

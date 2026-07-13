"""Executive Analytics — platform-wide stats for executive / founding-team access."""
import csv
import io
from datetime import date
from typing import Annotated

from fastapi import Depends, Query
from fastapi.responses import StreamingResponse
from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, get_db, require_executive

router = APIRouter(prefix="/admin/executive", tags=["executive"])


@router.get("/stats")
async def executive_stats(
    _: Annotated[CurrentUser, Depends(require_executive)],
    db: Annotated[AsyncSession, Depends(get_db)],
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    include_demo: bool = Query(False),
) -> dict:
    params: dict = {}
    claim_date = ""
    visit_date = ""
    lead_date = ""
    if date_from:
        claim_date += " AND service_date >= :date_from"
        visit_date += " AND visit_started_at::date >= :date_from"
        lead_date += " AND created_at::date >= :date_from"
        params["date_from"] = date_from
    if date_to:
        claim_date += " AND service_date <= :date_to"
        visit_date += " AND visit_started_at::date <= :date_to"
        lead_date += " AND created_at::date <= :date_to"
        params["date_to"] = date_to

    # Demo filters — empty string when include_demo=True to show all records
    _nd  = "" if include_demo else " AND NOT is_demo"        # users table, no alias
    _nu  = "" if include_demo else " AND NOT u.is_demo"      # users table, alias u
    _np  = "" if include_demo else " AND NOT p.is_demo"      # patients table, alias p
    _nl  = "" if include_demo else " AND NOT is_demo"        # leads table
    _ne  = "" if include_demo else " AND NOT is_demo"        # enrollment_services, no alias
    _nes = "" if include_demo else " AND NOT es.is_demo"     # enrollment_services, alias es

    # ── Section A: Platform Health ────────────────────────────────────────────
    ph = await db.execute(text(f"""
        SELECT
          COUNT(*) FILTER (WHERE role = 'provider' AND is_active{_nd})
            AS active_providers,
          COUNT(*) FILTER (WHERE role = 'provider' AND NOT is_active{_nd})
            AS inactive_providers,
          COUNT(*) FILTER (WHERE role = 'provider'{_nd})
            AS total_providers,
          COUNT(*) FILTER (WHERE role = 'provider'{_nd}
            AND subscription_status IN ('active', 'trialing'))
            AS subscribed_providers,
          COUNT(*) FILTER (WHERE role = 'provider'{_nd}
            AND subscription_status = 'past_due')
            AS past_due_providers,
          COUNT(*) FILTER (WHERE role = 'provider'{_nd}
            AND created_at >= NOW() - INTERVAL '30 days')
            AS new_providers_30d,
          COUNT(*) FILTER (WHERE role = 'provider'{_nd}
            AND created_at >= NOW() - INTERVAL '90 days')
            AS new_providers_90d,
          COUNT(*) FILTER (WHERE role = 'provider'{_nd}
            AND last_sign_in_at >= NOW() - INTERVAL '30 days')
            AS active_last_30d,
          COUNT(*) FILTER (WHERE role = 'provider'{_nd}
            AND last_sign_in_at >= NOW() - INTERVAL '90 days')
            AS active_last_90d,
          COUNT(DISTINCT billing_provider_id)
            FILTER (WHERE role = 'provider' AND billing_provider_id IS NOT NULL)
            AS active_agencies
        FROM public.users
    """))
    ph_row = ph.fetchone()

    # Cohort retention — last 12 monthly cohorts
    cohort_rows = await db.execute(text(f"""
        SELECT
          DATE_TRUNC('month', created_at)::date AS cohort_month,
          COUNT(*) AS cohort_size,
          COUNT(*) FILTER (
            WHERE is_active AND last_sign_in_at >= NOW() - INTERVAL '30 days'
          ) AS still_active
        FROM public.users
        WHERE role = 'provider'{_nd}
          AND created_at >= NOW() - INTERVAL '12 months'
        GROUP BY cohort_month
        ORDER BY cohort_month
    """))
    cohort_retention = [
        {
            "cohort_month": str(r.cohort_month),
            "cohort_size": int(r.cohort_size),
            "still_active": int(r.still_active),
            "retention_pct": round(100.0 * int(r.still_active) / max(int(r.cohort_size), 1), 1),
        }
        for r in cohort_rows.fetchall()
    ]

    # First-claim latency
    latency_row = await db.execute(text(f"""
        SELECT
          ROUND(AVG(days_to_first)::numeric, 1) AS avg_days,
          ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY days_to_first)::numeric, 1)
            AS median_days,
          COUNT(*) AS providers_with_claims
        FROM (
          SELECT
            u.id,
            EXTRACT(EPOCH FROM (MIN(c.created_at) - u.created_at)) / 86400
              AS days_to_first
          FROM public.users u
          JOIN public.claims c ON c.provider_id = u.id
          JOIN public.patients p ON c.patient_id = p.id
          WHERE u.role = 'provider'{_nu}{_np}
          GROUP BY u.id
        ) sub
    """))
    latency = latency_row.fetchone()

    never_billed_row = await db.execute(text(f"""
        SELECT COUNT(*) AS cnt
        FROM public.users u
        WHERE u.role = 'provider' AND u.is_active{_nu}
          AND NOT EXISTS (
            SELECT 1 FROM public.claims c WHERE c.provider_id = u.id
          )
    """))
    never_billed = never_billed_row.scalar() or 0

    first_claim_latency = {
        "avg_days": float(latency.avg_days) if latency and latency.avg_days else None,
        "median_days": float(latency.median_days) if latency and latency.median_days else None,
        "providers_with_claims": int(latency.providers_with_claims) if latency else 0,
        "providers_never_billed": int(never_billed),
    }

    # ── Section B: Lead Funnel ────────────────────────────────────────────────
    lead_rows = await db.execute(text(f"""
        SELECT
          source,
          COUNT(*) AS total,
          COUNT(*) FILTER (WHERE status = 'converted') AS converted,
          COUNT(*) FILTER (WHERE status = 'new') AS new,
          COUNT(*) FILTER (WHERE status = 'contacted') AS contacted,
          COUNT(*) FILTER (WHERE status = 'qualified') AS qualified,
          COUNT(*) FILTER (WHERE status = 'demo_scheduled') AS demo_scheduled,
          COUNT(*) FILTER (WHERE status = 'not_interested') AS not_interested
        FROM public.leads
        WHERE 1=1{_nl}{lead_date}
        GROUP BY source
        ORDER BY total DESC
    """), params)
    by_source = [
        {
            "source": r.source,
            "total": int(r.total),
            "converted": int(r.converted),
            "conversion_rate_pct": round(100.0 * int(r.converted) / max(int(r.total), 1), 1),
            "new": int(r.new),
            "contacted": int(r.contacted),
            "qualified": int(r.qualified),
            "demo_scheduled": int(r.demo_scheduled),
            "not_interested": int(r.not_interested),
        }
        for r in lead_rows.fetchall()
    ]
    lead_totals = await db.execute(text(f"""
        SELECT
          COUNT(*) AS total,
          COUNT(*) FILTER (WHERE status = 'converted') AS converted,
          COUNT(*) FILTER (WHERE status = 'new') AS new,
          COUNT(*) FILTER (WHERE status = 'demo_scheduled') AS demo_scheduled
        FROM public.leads
        WHERE 1=1{_nl}{lead_date}
    """), params)
    lt = lead_totals.fetchone()

    # ── Section C: Platform Claims & Revenue ──────────────────────────────────
    claims_summary = await db.execute(text(f"""
        SELECT
          COUNT(*) AS total_claims,
          COALESCE(SUM(c.billed_amount), 0) AS total_billed,
          COALESCE(SUM(c.paid_amount), 0) AS total_paid,
          COUNT(*) FILTER (WHERE c.status IN ('denied', 'rejected')) AS denied_claims,
          COUNT(*) FILTER (WHERE c.resubmit_count > 0) AS resubmitted_claims
        FROM public.claims c
        JOIN public.patients p ON c.patient_id = p.id
        WHERE 1=1{_np}{claim_date}
    """), params)
    cs = claims_summary.fetchone()
    total_billed = float(cs.total_billed) if cs else 0.0
    total_paid = float(cs.total_paid) if cs else 0.0

    # Visit type breakdown
    vt_rows = await db.execute(text(f"""
        SELECT
          c.visit_type,
          COUNT(*) AS claim_count,
          COALESCE(SUM(c.billed_amount), 0) AS total_billed,
          COALESCE(SUM(c.paid_amount), 0) AS total_paid
        FROM public.claims c
        JOIN public.patients p ON c.patient_id = p.id
        WHERE 1=1{_np}{claim_date}
        GROUP BY c.visit_type
        ORDER BY claim_count DESC
    """), params)
    # Rate lookup by visit type prefix
    _RATES = {"labor": 1000, "prenatal": 100, "postnatal": 100, "crisis": 175}
    def _rate(vt: str | None) -> int:
        if not vt:
            return 0
        for k, v in _RATES.items():
            if vt.startswith(k):
                return v
        return 0

    visit_type_breakdown = [
        {
            "visit_type": r.visit_type,
            "rate_per_visit": _rate(r.visit_type),
            "claim_count": int(r.claim_count),
            "total_billed": float(r.total_billed),
            "total_paid": float(r.total_paid),
            "collection_rate_pct": round(
                100.0 * float(r.total_paid) / max(float(r.total_billed), 0.01), 1
            ),
        }
        for r in vt_rows.fetchall()
    ]

    # Claim aging buckets (unpaid only)
    aging_rows = await db.execute(text(f"""
        SELECT
          CASE
            WHEN CURRENT_DATE - service_date <= 30  THEN '0-30'
            WHEN CURRENT_DATE - service_date <= 60  THEN '31-60'
            WHEN CURRENT_DATE - service_date <= 90  THEN '61-90'
            WHEN CURRENT_DATE - service_date <= 120 THEN '91-120'
            WHEN CURRENT_DATE - service_date <= 180 THEN '121-180'
            ELSE '180+'
          END AS age_bucket,
          COUNT(*) AS claim_count,
          COALESCE(SUM(c.billed_amount), 0) AS total_billed,
          MIN(CURRENT_DATE - service_date) AS min_age
        FROM public.claims c
        JOIN public.patients p ON c.patient_id = p.id
        WHERE c.submitted_at IS NULL
          AND (c.status IS NULL OR c.status NOT IN ('paid', 'approved'))
          AND c.service_date IS NOT NULL{_np}
        GROUP BY age_bucket
        ORDER BY min_age
    """))
    claim_aging = [
        {
            "age_bucket": r.age_bucket,
            "claim_count": int(r.claim_count),
            "total_billed": float(r.total_billed),
        }
        for r in aging_rows.fetchall()
    ]

    # ── Section D: Enrollment Pipeline ────────────────────────────────────────
    enroll_rows = await db.execute(text(f"""
        SELECT
          stage,
          status,
          COUNT(*) AS count,
          COUNT(*) FILTER (WHERE pcb_pathway = 'education_training') AS edu_pathway,
          COUNT(*) FILTER (WHERE pcb_pathway = 'experienced') AS exp_pathway,
          COUNT(*) FILTER (WHERE assigned_to_billing_admin) AS assigned_to_agency
        FROM public.enrollment_services
        WHERE 1=1{_ne}
        GROUP BY stage, status
        ORDER BY stage, status
    """))
    enrollment_by_stage = [
        {
            "stage": r.stage,
            "status": r.status,
            "count": int(r.count),
            "edu_pathway": int(r.edu_pathway),
            "exp_pathway": int(r.exp_pathway),
            "assigned_to_agency": int(r.assigned_to_agency),
        }
        for r in enroll_rows.fetchall()
    ]

    # Stage completion time
    completion_rows = await db.execute(text("""
        SELECT
          es.stage,
          COUNT(*) AS completed_count,
          ROUND(AVG(
            EXTRACT(EPOCH FROM (es.updated_at - es.created_at)) / 86400
          )::numeric, 1) AS avg_days,
          ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY EXTRACT(EPOCH FROM (es.updated_at - es.created_at)) / 86400
          )::numeric, 1) AS median_days
        FROM public.enrollment_services es
        WHERE es.status = 'complete'{_nes}
        GROUP BY es.stage
        ORDER BY avg_days DESC NULLS LAST
    """))
    stage_completion_time = [
        {
            "stage": r.stage,
            "completed_count": int(r.completed_count),
            "avg_days": float(r.avg_days) if r.avg_days else None,
            "median_days": float(r.median_days) if r.median_days else None,
        }
        for r in completion_rows.fetchall()
    ]

    # Enrollment tier penetration
    tier_row = await db.execute(text("""
        SELECT
          COUNT(*) AS total_agencies,
          COUNT(*) FILTER (WHERE enrollment_tier_enabled) AS tier_enabled,
          COUNT(*) FILTER (WHERE subscription_status IN ('active','trialing'))
            AS active_agencies
        FROM public.billing_providers
    """))
    tr = tier_row.fetchone()

    # ── Section E: Compliance Health ──────────────────────────────────────────
    compliance_row = await db.execute(text(f"""
        SELECT
          COUNT(*) FILTER (
            WHERE c.submitted_at IS NULL
              AND (c.status IS NULL OR c.status NOT IN ('paid','approved'))
              AND c.service_date IS NOT NULL
              AND c.service_date + INTERVAL '180 days' < CURRENT_DATE
          ) AS overdue_claims,
          COUNT(*) FILTER (
            WHERE c.submitted_at IS NULL
              AND (c.status IS NULL OR c.status NOT IN ('paid','approved'))
              AND c.service_date IS NOT NULL
              AND c.service_date + INTERVAL '150 days' < CURRENT_DATE
              AND c.service_date + INTERVAL '180 days' >= CURRENT_DATE
          ) AS urgent_claims,
          COUNT(*) FILTER (WHERE c.resubmit_count > 0) AS resubmitted_claims
        FROM public.claims c
        JOIN public.patients p ON c.patient_id = p.id
        WHERE 1=1{_np}{claim_date}
    """), params)
    comp = compliance_row.fetchone()

    ma91_row = await db.execute(text(f"""
        SELECT
          COUNT(*) AS total_visits,
          COUNT(*) FILTER (WHERE v.ma91_status = 'signed') AS signed,
          COUNT(*) FILTER (WHERE v.ma91_status = 'pending') AS pending,
          COUNT(*) FILTER (WHERE v.ma91_status = 'declined') AS declined,
          COUNT(*) FILTER (WHERE v.ma91_status IS NULL) AS missing
        FROM public.visits v
        JOIN public.patients p ON v.patient_id = p.id
        WHERE v.visit_started_at IS NOT NULL{_np}{visit_date}
    """), params)
    ma = ma91_row.fetchone()

    return {
        "platform_health": {
            "active_providers": int(ph_row.active_providers) if ph_row else 0,
            "inactive_providers": int(ph_row.inactive_providers) if ph_row else 0,
            "total_providers": int(ph_row.total_providers) if ph_row else 0,
            "subscribed_providers": int(ph_row.subscribed_providers) if ph_row else 0,
            "past_due_providers": int(ph_row.past_due_providers) if ph_row else 0,
            "new_providers_30d": int(ph_row.new_providers_30d) if ph_row else 0,
            "new_providers_90d": int(ph_row.new_providers_90d) if ph_row else 0,
            "active_last_30d": int(ph_row.active_last_30d) if ph_row else 0,
            "active_last_90d": int(ph_row.active_last_90d) if ph_row else 0,
            "active_agencies": int(ph_row.active_agencies) if ph_row else 0,
        },
        "cohort_retention": cohort_retention,
        "first_claim_latency": first_claim_latency,
        "lead_funnel": {
            "by_source": by_source,
            "totals": {
                "total": int(lt.total) if lt else 0,
                "converted": int(lt.converted) if lt else 0,
                "new": int(lt.new) if lt else 0,
                "demo_scheduled": int(lt.demo_scheduled) if lt else 0,
                "conversion_rate_pct": round(
                    100.0 * (int(lt.converted) if lt else 0) / max(int(lt.total) if lt else 0, 1), 1
                ),
            },
        },
        "claims_revenue": {
            "total_claims": int(cs.total_claims) if cs else 0,
            "total_billed": total_billed,
            "total_paid": total_paid,
            "collection_rate_pct": round(100.0 * total_paid / max(total_billed, 0.01), 1),
            "denied_claims": int(cs.denied_claims) if cs else 0,
            "platform_denial_rate_pct": round(
                100.0 * (int(cs.denied_claims) if cs else 0) / max(int(cs.total_claims) if cs else 0, 1), 1
            ),
            "resubmitted_claims": int(cs.resubmitted_claims) if cs else 0,
            "visit_type_breakdown": visit_type_breakdown,
            "claim_aging": claim_aging,
        },
        "enrollment_pipeline": {
            "by_stage": enrollment_by_stage,
            "stage_completion_time": stage_completion_time,
            "enrollment_tier": {
                "total_agencies": int(tr.total_agencies) if tr else 0,
                "tier_enabled": int(tr.tier_enabled) if tr else 0,
                "active_agencies": int(tr.active_agencies) if tr else 0,
                "penetration_pct": round(
                    100.0 * (int(tr.tier_enabled) if tr else 0)
                    / max(int(tr.active_agencies) if tr else 0, 1), 1
                ),
            },
        },
        "compliance_health": {
            "overdue_claims": int(comp.overdue_claims) if comp else 0,
            "urgent_claims": int(comp.urgent_claims) if comp else 0,
            "resubmitted_claims": int(comp.resubmitted_claims) if comp else 0,
            "ma91": {
                "total_visits": int(ma.total_visits) if ma else 0,
                "signed": int(ma.signed) if ma else 0,
                "pending": int(ma.pending) if ma else 0,
                "declined": int(ma.declined) if ma else 0,
                "missing": int(ma.missing) if ma else 0,
                "compliance_rate_pct": round(
                    100.0 * (int(ma.signed) if ma else 0) / max(int(ma.total_visits) if ma else 0, 1), 1
                ),
            },
        },
    }


@router.get("/mco-report")
async def mco_report(
    _: Annotated[CurrentUser, Depends(require_executive)],
    db: Annotated[AsyncSession, Depends(get_db)],
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    include_demo: bool = Query(False),
) -> dict:
    params: dict = {}
    date_clause = ""
    if date_from:
        date_clause += " AND c.service_date >= :date_from"
        params["date_from"] = date_from
    if date_to:
        date_clause += " AND c.service_date <= :date_to"
        params["date_to"] = date_to

    _np = "" if include_demo else " AND NOT p.is_demo"

    mco_rows = await db.execute(text(f"""
        SELECT
          LOWER(TRIM(p.mco))                                 AS mco_key,
          p.mco                                              AS mco_name,
          COUNT(DISTINCT c.patient_id)                       AS covered_patients,
          COUNT(DISTINCT c.provider_id)                      AS provider_count,
          COUNT(c.id)                                        AS total_claims,
          COALESCE(SUM(c.billed_amount), 0)                  AS total_billed,
          COALESCE(SUM(c.paid_amount), 0)                    AS total_paid,
          COUNT(*) FILTER (WHERE c.status IN ('denied','rejected'))
                                                             AS denied_claims,
          COUNT(*) FILTER (WHERE c.resubmit_count > 0)       AS resubmitted_claims,
          ROUND(AVG(
            CASE WHEN c.status IN ('paid','approved') AND r.payment_date IS NOT NULL
                 THEN (r.payment_date - c.service_date) END
          ), 1)                                              AS avg_days_to_pay
        FROM public.claims c
        JOIN public.patients p ON c.patient_id = p.id
        LEFT JOIN public.remittances r ON c.remittance_id = r.id
        WHERE 1=1{_np}{date_clause}
        GROUP BY LOWER(TRIM(p.mco)), p.mco
        ORDER BY total_billed DESC
    """), params)

    mco_data = []
    for r in mco_rows.fetchall():
        tb = float(r.total_billed)
        tp = float(r.total_paid)
        tc = int(r.total_claims)
        mco_data.append({
            "mco_name": r.mco_name or "Unknown",
            "covered_patients": int(r.covered_patients),
            "provider_count": int(r.provider_count),
            "total_claims": tc,
            "total_billed": tb,
            "total_paid": tp,
            "collection_rate_pct": round(100.0 * tp / max(tb, 0.01), 1),
            "denied_claims": int(r.denied_claims),
            "denial_rate_pct": round(100.0 * int(r.denied_claims) / max(tc, 1), 1),
            "resubmitted_claims": int(r.resubmitted_claims),
            "resubmission_rate_pct": round(100.0 * int(r.resubmitted_claims) / max(tc, 1), 1),
            "avg_days_to_pay": float(r.avg_days_to_pay) if r.avg_days_to_pay else None,
        })

    # Referring provider analysis
    ref_rows = await db.execute(text("""
        SELECT
          p.referring_provider_npi,
          p.referring_provider_name,
          COUNT(DISTINCT p.id)           AS total_patients,
          COUNT(DISTINCT p.provider_id)  AS doula_count
        FROM public.patients p
        WHERE p.referring_provider_npi IS NOT NULL
          AND p.is_active{_np}
        GROUP BY p.referring_provider_npi, p.referring_provider_name
        ORDER BY total_patients DESC
        LIMIT 50
    """))
    referring_providers = [
        {
            "npi": r.referring_provider_npi,
            "name": r.referring_provider_name,
            "total_patients": int(r.total_patients),
            "doula_count": int(r.doula_count),
        }
        for r in ref_rows.fetchall()
    ]

    # Telehealth vs in-person
    location_rows = await db.execute(text(f"""
        SELECT
          COALESCE(v.location_type, 'unknown') AS location_type,
          COUNT(*) AS visit_count,
          COUNT(DISTINCT v.provider_id) AS provider_count
        FROM public.visits v
        JOIN public.patients p ON v.patient_id = p.id
        WHERE v.visit_started_at IS NOT NULL{_np}
        GROUP BY location_type
        ORDER BY visit_count DESC
    """))
    location_split = [
        {
            "location_type": r.location_type,
            "visit_count": int(r.visit_count),
            "provider_count": int(r.provider_count),
        }
        for r in location_rows.fetchall()
    ]

    return {
        "mco_breakdown": mco_data,
        "referring_providers": referring_providers,
        "location_split": location_split,
    }


@router.get("/generate-report")
async def generate_executive_report(
    user: Annotated[CurrentUser, Depends(require_executive)],
    db: Annotated[AsyncSession, Depends(get_db)],
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    include_demo: bool = Query(False),
) -> StreamingResponse:
    from app.services.executive_report_service import stream_executive_report

    if date_from and date_to:
        period_label = f"{date_from} to {date_to}"
    elif date_from:
        period_label = f"from {date_from}"
    elif date_to:
        period_label = f"through {date_to}"
    else:
        period_label = "All Time"

    async def _generate():
        stats = await executive_stats(user, db, date_from, date_to, include_demo)
        mco = await mco_report(user, db, date_from, date_to, include_demo)
        async for chunk in stream_executive_report(stats, mco, period_label):
            yield chunk

    return StreamingResponse(
        _generate(),
        media_type="text/plain; charset=utf-8",
    )


@router.get("/mco-report.csv")
async def mco_report_csv(
    _: Annotated[CurrentUser, Depends(require_executive)],
    db: Annotated[AsyncSession, Depends(get_db)],
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    include_demo: bool = Query(False),
) -> StreamingResponse:
    report = await mco_report(_, db, date_from, date_to, include_demo)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "MCO", "Covered Patients", "Provider Count", "Total Claims",
        "Total Billed ($)", "Total Paid ($)", "Collection Rate (%)",
        "Denied Claims", "Denial Rate (%)", "Resubmitted Claims",
        "Resubmission Rate (%)", "Avg Days to Pay",
    ])
    for row in report["mco_breakdown"]:
        writer.writerow([
            row["mco_name"],
            row["covered_patients"],
            row["provider_count"],
            row["total_claims"],
            f"{row['total_billed']:.2f}",
            f"{row['total_paid']:.2f}",
            f"{row['collection_rate_pct']}%",
            row["denied_claims"],
            f"{row['denial_rate_pct']}%",
            row["resubmitted_claims"],
            f"{row['resubmission_rate_pct']}%",
            row["avg_days_to_pay"] if row["avg_days_to_pay"] is not None else "N/A",
        ])

    buf.seek(0)
    today = date.today().isoformat()
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="doulashield-mco-report-{today}.csv"'},
    )

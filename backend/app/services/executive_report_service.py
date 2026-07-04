"""AI-generated strategic report for the Executive Dashboard."""
import logging
from datetime import date
from typing import AsyncGenerator

import anthropic

from app.core.config import settings

log = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a strategic analyst advising the founding team of DoulaShield, "
    "a Pennsylvania Medicaid SaaS platform for Type 13 doula providers. "
    "Doulas submit claims to nine PA Managed Care Organizations: labor support (T1033, $1,000), "
    "prenatal visits (T1032 U7, $100 each, max 6), postnatal visits (T1032 U8, $100 each, max 6), "
    "and crisis/bereavement visits (T1032 U9, $175 each). "
    "The platform handles credentialing (PCB, NPPES, PROMISe Stage 2), MCO contracting (Stage 3), "
    "and Availity claim submission.\n\n"
    "Write a strategic report in Markdown with exactly these seven sections — use these exact headings:\n"
    "## Executive Summary\n"
    "## Platform Health Assessment\n"
    "## Revenue & Collections\n"
    "## MCO Contract Intelligence\n"
    "## Operational Risks\n"
    "## Strategic Recommendations\n"
    "## Quick Wins\n\n"
    "Guidance per section:\n"
    "- Executive Summary: 2-3 tight paragraphs — overall health verdict, biggest strength, biggest threat\n"
    "- Platform Health Assessment: growth trajectory, login vs. billing engagement gap, activation friction\n"
    "- Revenue & Collections: collection rate vs. 80-85% benchmark, claim aging dollar risk, visit type mix\n"
    "- MCO Contract Intelligence: identify 2-3 MCOs to prioritize for renegotiation with specific data points; "
    "note which are performing well; >20% denial rate and >45 avg days to pay are negotiation leverage\n"
    "- Operational Risks: top 3 risks each with severity (HIGH/MEDIUM/LOW), the metric that reveals it, "
    "and a concrete mitigation step\n"
    "- Strategic Recommendations: top 5, each formatted as **Title** — what to do, why it matters "
    "(cite the specific metric), and which KPI it moves\n"
    "- Quick Wins: 3-5 actions completable within 30 days, one sentence each\n\n"
    "Rules: cite specific figures; use Markdown bold for key numbers; no filler phrases or vague generalizations; "
    "if a metric is zero or absent, note it and recommend action; total length 700-1000 words."
)


def _build_context(stats: dict, mco: dict, period_label: str) -> str:
    ph = stats.get("platform_health", {})
    lf = stats.get("lead_funnel", {})
    lf_totals = lf.get("totals", {})
    cr = stats.get("claims_revenue", {})
    ep = stats.get("enrollment_pipeline", {})
    ep_tier = ep.get("enrollment_tier", {})
    ch = stats.get("compliance_health", {})
    ch_ma91 = ch.get("ma91", {})
    latency = stats.get("first_claim_latency", {})
    cohort = stats.get("cohort_retention", [])
    mco_list = mco.get("mco_breakdown", [])
    loc = mco.get("location_split", [])

    lines: list[str] = []
    today = date.today().isoformat()

    lines.append(f"PERIOD: {period_label}")
    lines.append(f"DATE: {today}\n")

    # Platform health
    lines.append("=== PLATFORM HEALTH (ALL-TIME) ===")
    lines.append(
        f"Providers: {ph.get('active_providers', 0)} active | "
        f"{ph.get('inactive_providers', 0)} inactive | "
        f"{ph.get('total_providers', 0)} total"
    )
    lines.append(
        f"Subscriptions: {ph.get('subscribed_providers', 0)} active | "
        f"{ph.get('past_due_providers', 0)} past due"
    )
    lines.append(f"Agencies: {ph.get('active_agencies', 0)}")
    lines.append(
        f"New providers: {ph.get('new_providers_30d', 0)} (last 30d) / "
        f"{ph.get('new_providers_90d', 0)} (last 90d)"
    )
    lines.append(
        f"Login activity: {ph.get('active_last_30d', 0)} logged in last 30d / "
        f"{ph.get('active_last_90d', 0)} last 90d"
    )

    avg_d = latency.get("avg_days")
    med_d = latency.get("median_days")
    lines.append(
        f"\nActivation (time to first claim): avg={avg_d}d | median={med_d}d | "
        f"never billed={latency.get('providers_never_billed', 0)}"
    )

    if cohort:
        lines.append("\nCohort retention (last 12 months):")
        for r in cohort:
            lines.append(
                f"  {str(r['cohort_month'])[:7]}: "
                f"{r['cohort_size']} signed up, "
                f"{r['still_active']} still active ({r['retention_pct']}%)"
            )

    # Lead funnel
    lines.append("\n=== LEAD FUNNEL ===")
    lines.append(
        f"Total: {lf_totals.get('total', 0)} | "
        f"Converted: {lf_totals.get('converted', 0)} ({lf_totals.get('conversion_rate_pct', 0)}%) | "
        f"Demo scheduled: {lf_totals.get('demo_scheduled', 0)} | "
        f"New/uncontacted: {lf_totals.get('new', 0)}"
    )
    by_source = lf.get("by_source", [])
    if by_source:
        lines.append("By source:")
        for r in by_source:
            lines.append(
                f"  {r['source']}: {r['total']} total, "
                f"{r['converted']} converted ({r['conversion_rate_pct']}%)"
            )

    # Claims & revenue
    total_billed = cr.get("total_billed", 0) or 0
    total_paid = cr.get("total_paid", 0) or 0
    lines.append("\n=== CLAIMS & REVENUE ===")
    lines.append(
        f"Claims: {cr.get('total_claims', 0)} | "
        f"Billed: ${total_billed:,.0f} | "
        f"Collected: ${total_paid:,.0f}"
    )
    lines.append(
        f"Collection rate: {cr.get('collection_rate_pct', 0)}% (benchmark ~80-85%)"
    )
    lines.append(
        f"Denial rate: {cr.get('platform_denial_rate_pct', 0)}% "
        f"({cr.get('denied_claims', 0)} claims denied)"
    )

    vt = cr.get("visit_type_breakdown", [])
    if vt:
        lines.append("\nBy visit type:")
        for r in vt:
            lines.append(
                f"  {r['visit_type']}: ${r['rate_per_visit']}/visit, "
                f"{r['claim_count']} claims, "
                f"${r['total_billed']:,.0f} billed, "
                f"{r['collection_rate_pct']}% collected"
            )

    aging = cr.get("claim_aging", [])
    if aging:
        total_aging = sum(r["total_billed"] for r in aging)
        lines.append(f"\nUnpaid claim aging (${total_aging:,.0f} total at risk):")
        for r in aging:
            lines.append(
                f"  {r['age_bucket']} days: {r['claim_count']} claims, "
                f"${r['total_billed']:,.0f}"
            )

    # MCO data
    if mco_list:
        lines.append("\n=== MCO CONTRACT DATA ===")
        for r in mco_list:
            avg_pay = f"{r['avg_days_to_pay']}d" if r["avg_days_to_pay"] is not None else "N/A"
            lines.append(
                f"  {r['mco_name']}: "
                f"{r['covered_patients']} patients, "
                f"{r['total_claims']} claims, "
                f"${r['total_billed']:,.0f} billed, "
                f"{r['collection_rate_pct']}% collected, "
                f"{r['denial_rate_pct']}% denial rate, "
                f"{r['resubmission_rate_pct']}% resubmitted, "
                f"avg {avg_pay} to pay"
            )

    if loc:
        total_visits = sum(r["visit_count"] for r in loc)
        lines.append("\nDelivery mode:")
        for r in loc:
            pct = round(100 * r["visit_count"] / max(total_visits, 1))
            lines.append(f"  {r['location_type']}: {r['visit_count']} visits ({pct}%)")

    # Enrollment pipeline
    lines.append("\n=== ENROLLMENT PIPELINE ===")
    lines.append(
        f"Enrollment tier: {ep_tier.get('tier_enabled', 0)}/{ep_tier.get('active_agencies', 0)} "
        f"agencies ({ep_tier.get('penetration_pct', 0)}% penetration)"
    )
    sct = ep.get("stage_completion_time", [])
    if sct:
        lines.append("Stage completion times:")
        for r in sct:
            lines.append(
                f"  {r['stage']}: avg {r['avg_days']}d | median {r['median_days']}d "
                f"({r['completed_count']} completed)"
            )

    # Compliance
    lines.append("\n=== COMPLIANCE ===")
    lines.append(
        f"Overdue claims (180d+): {ch.get('overdue_claims', 0)} | "
        f"Urgent (150-180d): {ch.get('urgent_claims', 0)}"
    )
    lines.append(
        f"MA91 compliance: {ch_ma91.get('compliance_rate_pct', 0)}% "
        f"({ch_ma91.get('signed', 0)}/{ch_ma91.get('total_visits', 0)} visits signed)"
    )
    lines.append(f"Resubmitted claims: {ch.get('resubmitted_claims', 0)}")

    return "\n".join(lines)


async def stream_executive_report(
    stats: dict,
    mco: dict,
    period_label: str,
) -> AsyncGenerator[bytes, None]:
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    context = _build_context(stats, mco, period_label)
    try:
        async with client.messages.stream(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": context}],
        ) as stream:
            async for text in stream.text_stream:
                yield text.encode("utf-8")
    except Exception:
        log.exception("Executive report generation failed")
        yield b"\n\n*Report generation failed — please try again.*"

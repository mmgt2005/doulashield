"""
Medicaid Audit Packet PDF generator.

Produces a self-contained multi-section PDF containing all documentation
needed for a PA Medicaid claim-level audit, then appends the CMS 1500 form.

Sections:
  Cover / Claim Summary
  1 — Member Information & Eligibility Verification
  2 — Service Documentation (SOAP + visit times + location)
  3 — MA 91 Patient Encounter Certification
  4 — Provider Credentials & Qualifications
  5 — Billing Record
  [CMS 1500 appended as final pages]
"""
import io
import json
from datetime import date, timedelta
from typing import Any

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services import cms1500_service

# ── Page geometry ─────────────────────────────────────────────────────────────
_LM = _RM = 0.75 * inch
_PAGE_W = letter[0] - _LM - _RM  # usable width

# ── Styles ────────────────────────────────────────────────────────────────────
_BASE = getSampleStyleSheet()

_COVER_TITLE = ParagraphStyle(
    "CoverTitle", parent=_BASE["Heading1"],
    fontSize=18, spaceAfter=4, alignment=1,
    textColor=colors.HexColor("#1e3a5f"),
)
_CONF = ParagraphStyle(
    "Conf", parent=_BASE["Normal"],
    fontSize=8, textColor=colors.HexColor("#b91c1c"), alignment=1,
)
_H2 = ParagraphStyle(
    "H2", parent=_BASE["Heading2"],
    fontSize=11, spaceAfter=4,
    textColor=colors.HexColor("#1e40af"),
)
_BODY = ParagraphStyle(
    "Body", parent=_BASE["Normal"],
    fontSize=9, leading=13, spaceAfter=3,
)
_SMALL = ParagraphStyle(
    "Small", parent=_BASE["Normal"],
    fontSize=8, leading=11, textColor=colors.HexColor("#374151"),
)
_LABEL = ParagraphStyle(
    "Label", parent=_BASE["Normal"],
    fontSize=8, textColor=colors.HexColor("#6b7280"), spaceAfter=1,
)

# ── Table style constants ─────────────────────────────────────────────────────
_HDR_STYLE = [
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, 0), 8),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
    ("FONTSIZE", (0, 1), (-1, -1), 8),
    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#94a3b8")),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
]

_KV_STYLE = [
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
    ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ("TOPPADDING", (0, 0), (-1, -1), 3),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_date(d: Any) -> str:
    if d is None:
        return "—"
    if isinstance(d, str):
        return d
    try:
        return d.strftime("%B %d, %Y")
    except Exception:
        return str(d)


def _fmt_dt(dt: Any) -> str:
    if dt is None:
        return "—"
    try:
        return dt.strftime("%B %d, %Y  %I:%M %p UTC")
    except Exception:
        return str(dt)


def _days_note(expiry: Any) -> str:
    if expiry is None:
        return "—"
    try:
        delta = (expiry - date.today()).days
        if delta < 0:
            return f"⚠ OVERDUE by {abs(delta)} days"
        if delta == 0:
            return "⚠ Expires TODAY"
        return f"{delta} days remaining"
    except Exception:
        return "—"


def _kv_table(rows: list[tuple[str, str]], label_w: float = 1.8 * inch) -> Table:
    data = [
        [Paragraph(f"<b>{k}</b>", _SMALL), Paragraph(str(v) if v is not None else "—", _BODY)]
        for k, v in rows
    ]
    t = Table(data, colWidths=[label_w, _PAGE_W - label_w])
    t.setStyle(TableStyle(_KV_STYLE))
    return t


def _section(title: str) -> list:
    return [
        Spacer(1, 0.15 * inch),
        Paragraph(title, _H2),
        HRFlowable(width=_PAGE_W, thickness=1, color=colors.HexColor("#1e40af"), spaceAfter=6),
    ]


def _proc_code(visit_type: str) -> str:
    try:
        from app.core.billing_constants import billing_for_visit
        code, *_ = billing_for_visit(visit_type)
        return code
    except Exception:
        return "T1032"


def _modifier(visit_type: str) -> str:
    try:
        from app.core.billing_constants import billing_for_visit
        _, mod, *_ = billing_for_visit(visit_type)
        return mod or "—"
    except Exception:
        return "—"


# ── Main function ─────────────────────────────────────────────────────────────

def generate_audit_packet(
    patient_data: dict,
    visit_data: dict,
    provider_data: dict,
    claim_data: dict,
) -> bytes:
    """
    Build a Medicaid audit packet PDF and return raw bytes.

    Extra keys beyond the CMS 1500 dicts:
      patient_data:  eligibility_status, eligibility_checked_at,
                     medicaid_card_image_bytes
      visit_data:    visit_started_at (datetime), visit_ended_at (datetime),
                     birth_time, birth_location, birth_notes, entry,
                     ma91_signed_by_name, ma91_zipzign_request_id,
                     ma91_status, ma91_signature_bytes (bytes),
                     subjective, objective, assessment, plan
      provider_data: caqh_last_attested_on (date), promise_last_enrolled_on (date),
                     pcb_last_certified_on (date), liability_insurance_expires_on (date),
                     mco_contracts (list[dict])
      claim_data:    claim_id (str), availity_claim_id, is_manual (bool), status,
                     service_date, billed_amount, paid_amount, denial_reason,
                     submitted_at (datetime), remittance_id
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=_LM,
        rightMargin=_RM,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    story: list = []

    # Shortcuts
    patient_name = patient_data.get("name") or "—"
    medicaid_id = patient_data.get("medicaid_id") or "—"
    mco = patient_data.get("mco") or "—"
    visit_type = visit_data.get("visit_type") or ""
    svc_date = _fmt_date(visit_data.get("visit_date") or claim_data.get("service_date"))
    provider_npi = provider_data.get("npi") or "—"
    provider_name = provider_data.get("full_name") or "—"

    # ── Cover ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph("MEDICAID AUDIT PACKET", _COVER_TITLE))
    story.append(Paragraph("CONFIDENTIAL — PROTECTED HEALTH INFORMATION", _CONF))
    story.append(Spacer(1, 0.3 * inch))

    cover_rows = [
        ["Field", "Value"],
        ["Patient", patient_name],
        ["Medicaid ID", medicaid_id],
        ["MCO / Payer", mco],
        ["Service Date", svc_date],
        ["Visit Type", visit_type.replace("_", " ").title()],
        ["Procedure Code", _proc_code(visit_type)],
        ["Modifier", _modifier(visit_type)],
        ["Billed Amount", f"${claim_data.get('billed_amount')}" if claim_data.get("billed_amount") is not None else "—"],
        ["Claim Status", (claim_data.get("status") or "Not submitted").capitalize()],
        ["Provider NPI", provider_npi],
        ["Provider Name", provider_name],
        ["Packet Generated", date.today().strftime("%B %d, %Y")],
    ]
    cover_tbl = Table(cover_rows, colWidths=[1.8 * inch, _PAGE_W - 1.8 * inch])
    cover_tbl.setStyle(TableStyle(_HDR_STYLE + [("FONTSIZE", (0, 0), (-1, -1), 9)]))
    story.append(cover_tbl)
    story.append(PageBreak())

    # ── Section 1: Member Information & Eligibility ───────────────────────────
    story.extend(_section("Section 1 — Member Information & Eligibility Verification"))

    story.append(_kv_table([
        ("Patient Name", patient_name),
        ("Medicaid ID", medicaid_id),
        ("Date of Birth", _fmt_date(patient_data.get("date_of_birth"))),
        ("MCO / Plan", mco),
        ("Patient Address", patient_data.get("address") or "—"),
        ("Gender", "Female" if patient_data.get("gender") == "F" else
                   "Male" if patient_data.get("gender") == "M" else
                   patient_data.get("gender") or "—"),
        ("Has Other Insurance", "Yes" if patient_data.get("has_other_insurance") else "No"),
        ("Eligibility Status", (patient_data.get("eligibility_status") or "Not verified").capitalize()),
        ("Eligibility Last Verified", _fmt_dt(patient_data.get("eligibility_checked_at"))),
        ("Referring Provider NPI", patient_data.get("referring_provider_npi") or "—"),
        ("Referring Provider Name", patient_data.get("referring_provider_name") or "—"),
    ]))

    mc_bytes: bytes | None = patient_data.get("medicaid_card_image_bytes")
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("<b>Medicaid Card (scanned copy)</b>", _SMALL))
    if mc_bytes:
        try:
            img = Image(io.BytesIO(mc_bytes), width=3.0 * inch, height=1.9 * inch, kind="proportional")
            story.append(img)
        except Exception:
            story.append(Paragraph("(Medicaid card image could not be rendered)", _SMALL))
    else:
        story.append(Paragraph("No Medicaid card scan on file for this patient.", _SMALL))

    story.append(PageBreak())

    # ── Section 2: Service Documentation ─────────────────────────────────────
    story.extend(_section("Section 2 — Service Documentation"))

    loc_type = visit_data.get("location_type") or "in_person"
    if loc_type == "telehealth":
        pos_label = "Telehealth (Place of Service 02)"
    elif visit_data.get("alternate_location"):
        pos_label = f"Alternate Location: {visit_data['alternate_location']} (POS 12)"
    else:
        pos_label = "Patient Home (Place of Service 12)"

    # Duration calculation
    vs = visit_data.get("visit_started_at")
    ve = visit_data.get("visit_ended_at")
    duration_str = "—"
    if vs and ve:
        try:
            mins = int((ve - vs).total_seconds() // 60)
            h, m = divmod(mins, 60)
            duration_str = (f"{h}h {m}m" if h else f"{m} minutes") + (
                "  ⚠ Under 30-minute minimum" if mins < 30 else ""
            )
        except Exception:
            pass

    story.append(_kv_table([
        ("Visit Type", visit_type.replace("_", " ").title()),
        ("Service Date", svc_date),
        ("Place of Service", pos_label),
        ("Visit Started", _fmt_dt(vs)),
        ("Visit Ended", _fmt_dt(ve)),
        ("Duration", duration_str),
        ("Procedure Code", _proc_code(visit_type)),
        ("Modifier", _modifier(visit_type)),
        ("Prior Auth Number", visit_data.get("prior_auth_number") or "—"),
    ]))

    # SOAP Note
    soap_fields = [
        ("Subjective", "subjective"),
        ("Objective", "objective"),
        ("Assessment", "assessment"),
        ("Plan", "plan"),
    ]
    has_soap = any(visit_data.get(k) for _, k in soap_fields)
    if has_soap:
        story.append(Spacer(1, 0.12 * inch))
        story.append(Paragraph("<b>SOAP Note</b>", _SMALL))
        story.append(HRFlowable(width=_PAGE_W, thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=4))
        for label, key in soap_fields:
            val = visit_data.get(key)
            if val:
                story.append(Paragraph(f"<b>{label}:</b>", _LABEL))
                story.append(Paragraph(val, _BODY))

    entry = visit_data.get("entry")
    if entry:
        story.append(Spacer(1, 0.08 * inch))
        story.append(Paragraph("<b>Visit Notes:</b>", _LABEL))
        story.append(Paragraph(entry, _BODY))

    # Labor-specific fields
    if visit_type == "labor":
        labor_rows: list[tuple[str, str]] = []
        if visit_data.get("birth_time"):
            labor_rows.append(("Birth Time", str(visit_data["birth_time"])))
        if visit_data.get("birth_location"):
            labor_rows.append(("Birth Location", visit_data["birth_location"]))
        if visit_data.get("birth_notes"):
            labor_rows.append(("Birth / Delivery Notes", visit_data["birth_notes"]))
        if labor_rows:
            story.append(Spacer(1, 0.08 * inch))
            story.append(Paragraph("<b>Labor & Delivery Record</b>", _SMALL))
            story.append(_kv_table(labor_rows))

    story.append(PageBreak())

    # ── Section 3: MA 91 Certification ───────────────────────────────────────
    story.extend(_section("Section 3 — MA 91 Patient Encounter Certification"))

    MA91_TEXT = (
        "My signature certifies that I received a service or item on the date listed above. "
        "I understand that payment for this service will be from Federal and State funds, and that "
        "any false claims or concealment of material may be prosecuted under Federal and State laws."
    )
    story.append(Paragraph("Statutory Certification Text (MA 91):", _LABEL))
    story.append(Paragraph(f'<i>"{MA91_TEXT}"</i>', _BODY))
    story.append(Spacer(1, 0.1 * inch))

    ma91_status = visit_data.get("ma91_status") or "unsigned"
    ma91_rows: list[tuple[str, str]] = [
        ("Signature Status", ma91_status.capitalize()),
        ("Patient Name (at signing)", visit_data.get("ma91_signed_by_name") or "—"),
        ("Signed At", _fmt_dt(patient_data.get("ma91_signed_at"))),
    ]
    if visit_data.get("ma91_zipzign_request_id"):
        ma91_rows.append(("ZipZign Request ID (e-signature)", visit_data["ma91_zipzign_request_id"]))

    story.append(_kv_table(ma91_rows))

    ma91_sig: bytes | None = patient_data.get("ma91_signature_bytes")
    if ma91_sig:
        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph("<b>Patient Signature Image:</b>", _SMALL))
        try:
            sig_img = Image(io.BytesIO(ma91_sig), width=2.5 * inch, height=1.0 * inch, kind="proportional")
            story.append(sig_img)
        except Exception:
            story.append(Paragraph("(Signature image unavailable)", _SMALL))

    story.append(PageBreak())

    # ── Section 4: Provider Credentials ──────────────────────────────────────
    story.extend(_section("Section 4 — Provider Credentials & Qualifications"))

    caqh_date = provider_data.get("caqh_last_attested_on")
    caqh_expiry = (caqh_date + timedelta(days=90)) if caqh_date else None
    promise_date = provider_data.get("promise_last_enrolled_on")
    promise_expiry = (promise_date + timedelta(days=1825)) if promise_date else None
    pcb_date = provider_data.get("pcb_last_certified_on")
    pcb_expiry = (pcb_date + timedelta(days=730)) if pcb_date else None
    liability_expiry = provider_data.get("liability_insurance_expires_on")

    story.append(_kv_table([
        ("Provider Legal Name", provider_name),
        ("NPI", provider_npi),
        ("Billing Provider Name", provider_data.get("billing_provider_name") or provider_name),
        ("Taxonomy Code", "374J00000X  (Certified Doula)"),
        ("PA Provider Type", "13 — Non-Traditional"),
        ("PA Specialty Code", "130 — Certified Doula"),
        ("CAQH Last Attested", _fmt_date(caqh_date)),
        ("CAQH Next Due (90-day cycle)",
         f"{_fmt_date(caqh_expiry)}  [{_days_note(caqh_expiry)}]"),
        ("PROMISe™ Last Enrolled", _fmt_date(promise_date)),
        ("PROMISe™ Next Due (5-year cycle)",
         f"{_fmt_date(promise_expiry)}  [{_days_note(promise_expiry)}]"),
        ("PCB Certification Date", _fmt_date(pcb_date)),
        ("PCB Next Due (2-year cycle)",
         f"{_fmt_date(pcb_expiry)}  [{_days_note(pcb_expiry)}]"),
        ("Liability Insurance Expires",
         f"{_fmt_date(liability_expiry)}  [{_days_note(liability_expiry)}]"),
    ]))

    # MCO Contracts
    mco_contracts = provider_data.get("mco_contracts") or []
    if isinstance(mco_contracts, str):
        try:
            mco_contracts = json.loads(mco_contracts)
        except Exception:
            mco_contracts = []

    if mco_contracts:
        story.append(Spacer(1, 0.12 * inch))
        story.append(Paragraph("<b>MCO Network Participation</b>", _SMALL))
        mco_rows = [["MCO", "Contract Effective Date"]]
        for c in mco_contracts:
            mco_rows.append([
                c.get("mco", ""),
                _fmt_date(c.get("contract_date")) if c.get("contract_date") else "—",
            ])
        mco_tbl = Table(mco_rows, colWidths=[3.2 * inch, _PAGE_W - 3.2 * inch])
        mco_tbl.setStyle(TableStyle(_HDR_STYLE))
        story.append(mco_tbl)

    story.append(PageBreak())

    # ── Section 5: Billing Record ─────────────────────────────────────────────
    story.extend(_section("Section 5 — Billing Record"))

    claim_id_str = str(claim_data.get("claim_id") or "")
    billed = claim_data.get("billed_amount")
    paid = claim_data.get("paid_amount")

    story.append(_kv_table([
        ("Internal Claim ID", claim_id_str or "—"),
        ("Availity Claim ID", claim_data.get("availity_claim_id") or "—"),
        ("Submission Type", "Manual (MCO Provider Portal)" if claim_data.get("is_manual") else "Availity EDI"),
        ("Claim Status", (claim_data.get("status") or "Not submitted").capitalize()),
        ("Service Date", svc_date),
        ("Billed Amount", f"${billed}" if billed is not None else "—"),
        ("Paid Amount", f"${paid}" if paid is not None else "—"),
        ("Denial / Adjustment Reason", claim_data.get("denial_reason") or "—"),
        ("Submitted At", _fmt_dt(claim_data.get("submitted_at"))),
        ("Remittance ID", str(claim_data.get("remittance_id") or "—")),
    ]))

    story.append(Spacer(1, 0.3 * inch))
    story.append(HRFlowable(width=_PAGE_W, thickness=0.5, color=colors.HexColor("#94a3b8"), spaceAfter=6))
    story.append(Paragraph(
        "This audit packet was generated by DoulaShield on "
        f"{date.today().strftime('%B %d, %Y')}. All documentation reflects provider-entered records. "
        "This packet is confidential and intended solely for authorized Medicaid audit purposes.",
        _SMALL,
    ))

    # ── Build narrative PDF ───────────────────────────────────────────────────
    doc.build(story)
    narrative_bytes = buf.getvalue()

    # ── Append CMS 1500 pages ─────────────────────────────────────────────────
    try:
        cms_bytes = cms1500_service.generate_pdf(
            patient_data=patient_data,
            visit_data=visit_data,
            provider_data=provider_data,
        )
    except Exception:
        cms_bytes = None

    if not cms_bytes:
        return narrative_bytes

    writer = PdfWriter()
    for page in PdfReader(io.BytesIO(narrative_bytes)).pages:
        writer.add_page(page)
    # Only include the front of the CMS 1500 form (page 0); page 1 is the back/instructions
    cms_reader = PdfReader(io.BytesIO(cms_bytes))
    writer.add_page(cms_reader.pages[0])
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()

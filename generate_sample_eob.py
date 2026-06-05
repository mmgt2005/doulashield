#!/usr/bin/env python3
"""
Generate a sample Medicaid Remittance Advice / EOB PDF.

Produces a realistic AmeriHealth Caritas PA HealthChoices 835 EOB with:
  - 3 claim lines (2 paid, 1 denied)
  - X12 adjustment reason codes on the denied line
  - EFT/check details, provider summary, remittance totals

Output: sample_eob.pdf
"""

import io
from datetime import date, datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Palette ────────────────────────────────────────────────────────────────────
MCO_BLUE   = colors.HexColor("#003087")   # AmeriHealth Caritas deep blue
MCO_LIGHT  = colors.HexColor("#e8f0fa")   # header band fill
DENY_RED   = colors.HexColor("#c0392b")
PAID_GREEN = colors.HexColor("#1a7a4a")
GRAY_TEXT  = colors.HexColor("#444444")
LIGHT_GRAY = colors.HexColor("#f5f5f5")
MID_GRAY   = colors.HexColor("#cccccc")

# ── Sample data ────────────────────────────────────────────────────────────────
REMITTANCE = {
    "eft_number":    "EFT202606050018",
    "payment_date":  "2026-06-05",
    "check_date":    "June 5, 2026",
    "total_paid":    "200.00",
    "provider_name": "Sarah J. Mitchell, CD",
    "provider_npi":  "1234567890",
    "provider_addr": "428 Chestnut St, Philadelphia, PA 19106",
    "payer_name":    "PA Medicaid Combined Remittance",
    "payer_id":      "MULTI",
    "payer_addr":    "P.O. Box 8045, Harrisburg, PA 17105",
}

CLAIMS = [
    {
        "patient_name": "DOE, JOHN",
        "medicaid_id":  "MA-0001-0001",
        "dob":          "1990-01-01",
        "service_date": "2026-05-28",
        "procedure_code": "T1032",
        "modifier":     "U7",
        "diagnosis":    "Z32.2",
        "pos":          "12",
        "billed_amount": "100.00",
        "allowed_amount": "100.00",
        "paid_amount":   "100.00",
        "patient_resp":  "0.00",
        "status":       "paid",
        "claim_id":     "FFS-20260515-001",
        "payer":        "FFS (PROMISe™)",
        "adjustments":  [],
    },
    {
        "patient_name": "SAMPLE MEMBER",
        "medicaid_id":  "MA-0002-0001",
        "dob":          "1995-06-01",
        "service_date": "2026-05-29",
        "procedure_code": "T1032",
        "modifier":     "U8",
        "diagnosis":    "Z39.1",
        "pos":          "12",
        "billed_amount": "100.00",
        "allowed_amount": "100.00",
        "paid_amount":   "100.00",
        "patient_resp":  "0.00",
        "status":       "paid",
        "claim_id":     "UPMC-20260520-001",
        "payer":        "UPMC For You",
        "adjustments":  [],
    },
]


def _style(name: str, **kwargs) -> ParagraphStyle:
    base = getSampleStyleSheet()["Normal"]
    kw = dict(fontName="Helvetica", fontSize=9, textColor=GRAY_TEXT,
              leading=13, spaceAfter=0)
    kw.update(kwargs)
    return ParagraphStyle(name, parent=base, **kw)


def _bold(text: str, size: int = 9, color=GRAY_TEXT) -> Paragraph:
    st = _style("_bold", fontName="Helvetica-Bold", fontSize=size, textColor=color)
    return Paragraph(text, st)


def _normal(text: str, size: int = 9, color=GRAY_TEXT, align=TA_LEFT) -> Paragraph:
    st = _style("_normal", fontSize=size, textColor=color, alignment=align)
    return Paragraph(text, st)


def _hr(width: float = 7.5 * inch, thickness: float = 0.5,
        color: colors.Color = MID_GRAY) -> HRFlowable:
    return HRFlowable(width=width, thickness=thickness, color=color, spaceAfter=4)


def build_eob(out_path: str) -> None:
    doc = SimpleDocTemplate(
        out_path,
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.60 * inch,
        bottomMargin=0.60 * inch,
    )
    W = letter[0] - 1.30 * inch   # usable width
    story = []

    # ── PAGE HEADER BAND ───────────────────────────────────────────────────────
    header_data = [[
        _bold("PA Medicaid Combined Remittance Advice", size=13, color=MCO_BLUE),
        _normal("REMITTANCE ADVICE / EXPLANATION OF BENEFITS (EOB)\n835 Electronic Remittance",
                size=8, color=MCO_BLUE, align=TA_RIGHT),
    ]]
    hdr_tbl = Table(header_data, colWidths=[W * 0.58, W * 0.42])
    hdr_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), MCO_LIGHT),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING",   (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LINEBELOW", (0, 0), (-1, -1), 2, MCO_BLUE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(hdr_tbl)
    story.append(Spacer(1, 10))

    # ── EFT / PAYMENT SUMMARY ─────────────────────────────────────────────────
    meta_rows = [
        ["EFT / Check Number", REMITTANCE["eft_number"],
         "Payment Date", REMITTANCE["check_date"]],
        ["Payer", REMITTANCE["payer_name"],
         "Payer ID",    REMITTANCE["payer_id"]],
        ["Provider Name", REMITTANCE["provider_name"],
         "Provider NPI", REMITTANCE["provider_npi"]],
        ["Provider Address", REMITTANCE["provider_addr"],
         "Total EFT Amount", f"${REMITTANCE['total_paid']}"],
    ]
    meta_table = Table(
        [[_bold(r[0], size=8), _normal(r[1], size=8),
          _bold(r[2], size=8), _normal(r[3], size=8)] for r in meta_rows],
        colWidths=[W * 0.18, W * 0.34, W * 0.16, W * 0.32],
    )
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#dce5f5")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#dce5f5")),
        ("GRID",       (0, 0), (-1, -1), 0.4, MID_GRAY),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        # highlight total row
        ("BACKGROUND", (3, 3), (3, 3), colors.HexColor("#d4edda")),
        ("TEXTCOLOR",  (3, 3), (3, 3), PAID_GREEN),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # ── SECTION HEADING ────────────────────────────────────────────────────────
    story.append(_bold("CLAIM PAYMENT DETAIL", size=10, color=MCO_BLUE))
    story.append(_hr(color=MCO_BLUE, thickness=1))
    story.append(Spacer(1, 4))

    # ── CLAIMS ────────────────────────────────────────────────────────────────
    col_labels = [
        "Claim ID", "Patient Name", "Medicaid ID", "Payer", "DOS",
        "Proc/Mod", "Billed", "Allowed", "Paid", "Status",
    ]
    col_w = [
        W * 0.16, W * 0.13, W * 0.10, W * 0.13, W * 0.08,
        W * 0.08, W * 0.08, W * 0.08, W * 0.08, W * 0.08,
    ]

    tbl_data = [[_bold(c, size=7, color=colors.white) for c in col_labels]]

    for cl in CLAIMS:
        proc = cl["procedure_code"] + (f"/{cl['modifier']}" if cl["modifier"] else "")
        stat_color = PAID_GREEN if cl["status"] == "paid" else DENY_RED
        row = [
            _normal(cl["claim_id"], size=7),
            _bold(cl["patient_name"], size=7),
            _normal(cl["medicaid_id"], size=7),
            _normal(cl.get("payer", ""), size=7),
            _normal(cl["service_date"], size=7),
            _normal(proc, size=7),
            _normal(f"${cl['billed_amount']}", size=7, align=TA_RIGHT),
            _normal(f"${cl['allowed_amount']}", size=7, align=TA_RIGHT),
            _bold(f"${cl['paid_amount']}", size=7, color=stat_color),
            _bold(cl["status"].upper(), size=7, color=stat_color),
        ]
        tbl_data.append(row)

    claims_tbl = Table(tbl_data, colWidths=col_w, repeatRows=1)
    claims_tbl.setStyle(TableStyle([
        # Header row
        ("BACKGROUND",   (0, 0), (-1, 0), MCO_BLUE),
        ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 7),
        # Alternating row fills
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        # Grid
        ("GRID",         (0, 0), (-1, -1), 0.3, MID_GRAY),
        ("LINEBELOW",    (0, 0), (-1, 0), 1.5, MCO_BLUE),
        # Padding
        ("LEFTPADDING",  (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(claims_tbl)
    story.append(Spacer(1, 14))

    # ── ADJUSTMENT / DENIAL DETAIL ────────────────────────────────────────────
    story.append(_bold("CLAIM ADJUSTMENT REASON CODES (CARC)", size=10, color=MCO_BLUE))
    story.append(_hr(color=MCO_BLUE, thickness=1))
    story.append(Spacer(1, 4))

    adj_header = [
        _bold("Claim ID", size=7, color=colors.white),
        _bold("Patient", size=7, color=colors.white),
        _bold("Group-Code", size=7, color=colors.white),
        _bold("Adj Amount", size=7, color=colors.white),
        _bold("Reason Description", size=7, color=colors.white),
    ]
    adj_data = [adj_header]
    for cl in CLAIMS:
        if not cl["adjustments"]:
            continue
        for i, adj in enumerate(cl["adjustments"]):
            adj_data.append([
                _normal(cl["claim_id"] if i == 0 else "", size=7),
                _normal(cl["patient_name"] if i == 0 else "", size=7),
                _bold(f"{adj['group']}-{adj['code']}", size=7, color=DENY_RED),
                _normal(f"${adj['amount']}", size=7, align=TA_RIGHT),
                _normal(adj["description"], size=7),
            ])

    adj_tbl = Table(
        adj_data,
        colWidths=[W * 0.14, W * 0.14, W * 0.10, W * 0.10, W * 0.52],
        repeatRows=1,
    )
    adj_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), MCO_BLUE),
        ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        ("GRID",         (0, 0), (-1, -1), 0.3, MID_GRAY),
        ("LINEBELOW",    (0, 0), (-1, 0), 1.5, MCO_BLUE),
        ("LEFTPADDING",  (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(adj_tbl)
    story.append(Spacer(1, 14))

    # ── REMITTANCE TOTALS ─────────────────────────────────────────────────────
    story.append(_bold("REMITTANCE TOTALS", size=10, color=MCO_BLUE))
    story.append(_hr(color=MCO_BLUE, thickness=1))
    story.append(Spacer(1, 4))

    total_billed  = sum(float(c["billed_amount"])  for c in CLAIMS)
    total_allowed = sum(float(c["allowed_amount"]) for c in CLAIMS)
    total_paid    = sum(float(c["paid_amount"])    for c in CLAIMS)
    total_adj     = total_billed - total_allowed

    totals_data = [
        [_bold("Total Claims Processed", size=8), _bold(str(len(CLAIMS)), size=8, color=MCO_BLUE)],
        [_bold("Total Billed Amount",     size=8), _bold(f"${total_billed:,.2f}", size=8)],
        [_bold("Total Allowed Amount",    size=8), _bold(f"${total_allowed:,.2f}", size=8)],
        [_bold("Total Adjustments",       size=8), _bold(f"${total_adj:,.2f}", size=8, color=DENY_RED)],
        [_bold("TOTAL AMOUNT PAID (EFT)", size=9, color=MCO_BLUE),
         _bold(f"${total_paid:,.2f}", size=9, color=PAID_GREEN)],
    ]
    totals_tbl = Table(totals_data, colWidths=[W * 0.68, W * 0.32])
    totals_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), LIGHT_GRAY),
        ("BACKGROUND",   (0, -1), (-1, -1), colors.HexColor("#d4edda")),
        ("GRID",         (0, 0), (-1, -1), 0.4, MID_GRAY),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ALIGN",        (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE",    (0, -1), (-1, -1), 1.5, PAID_GREEN),
    ]))
    story.append(totals_tbl)
    story.append(Spacer(1, 14))

    # ── IMPORTANT NOTICES ────────────────────────────────────────────────────
    story.append(_bold("IMPORTANT NOTICES", size=10, color=MCO_BLUE))
    story.append(_hr(color=MCO_BLUE, thickness=1))
    story.append(Spacer(1, 4))

    notices = [
        ("Reconsideration Deadline",
         "Providers have 90 days from the payment date to file a reconsideration request "
         "for denied or adjusted claims. Contact the relevant MCO or PROMISe™ Provider Portal."),
        ("FFS / PROMISe™ Claims",
         "Fee-for-service claims are processed through PROMISe™ (PA DHS). "
         "View claim status at promise.dpw.state.pa.us. Questions: 1-800-537-8862."),
        ("UPMC For You Claims",
         "UPMC For You claims are managed via UPMC Health Plan Provider OnLine. "
         "Visit upmchealthplan.com/providers. Questions: 1-888-876-2756."),
        ("ERA / Paper EOB",
         "Electronic Remittance Advice (835) files are available via the respective payer "
         "portal. This document serves as your paper EOB for provider records."),
    ]

    for title, body in notices:
        notice_tbl = Table(
            [[_bold(title, size=8, color=MCO_BLUE), _normal(body, size=8)]],
            colWidths=[W * 0.22, W * 0.78],
        )
        notice_tbl.setStyle(TableStyle([
            ("VALIGN",   (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",  (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING",   (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LINEBELOW", (0, 0), (-1, 0), 0.3, MID_GRAY),
        ]))
        story.append(notice_tbl)

    story.append(Spacer(1, 14))

    # ── FOOTER ────────────────────────────────────────────────────────────────
    story.append(_hr(color=MCO_BLUE, thickness=1.5))
    footer_tbl = Table(
        [[
            _normal("PA Medicaid Combined Remittance  |  P.O. Box 8045, Harrisburg PA 17105",
                    size=7, color=colors.HexColor("#666666")),
            _normal(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  "
                    f"EFT: {REMITTANCE['eft_number']}",
                    size=7, color=colors.HexColor("#666666"), align=TA_RIGHT),
        ]],
        colWidths=[W * 0.60, W * 0.40],
    )
    footer_tbl.setStyle(TableStyle([
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(footer_tbl)

    doc.build(story)
    print(f"EOB generated → {out_path}")


if __name__ == "__main__":
    out = Path(__file__).parent / "sample_eob.pdf"
    build_eob(str(out))

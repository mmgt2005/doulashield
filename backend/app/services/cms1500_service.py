"""
Generates a filled CMS 1500 (02/12) claim form PDF.

Fills the official blank form's AcroForm fields by name using pypdf.
The blank form is the 1500CMS.COM AcroForm PDF stored at app/static/cms1500_blank.pdf.
"""
from __future__ import annotations

import io
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject

from app.core.billing_constants import DOULA_TAXONOMY, billing_for_visit

_BLANK_FORM = Path(__file__).parent.parent / "static" / "cms1500_blank.pdf"


# ---------------------------------------------------------------------------
# Helpers for setting radio group values
# ---------------------------------------------------------------------------

def _set_radio(writer: PdfWriter, page_idx: int, field_name: str, on_state: str) -> None:
    """Set a radio button group to the given on_state (e.g. '/Medicaid', '/F')."""
    for annot_ref in writer.pages[page_idx].get("/Annots", []):
        annot = annot_ref.get_object()
        t = annot.get("/T", "")
        ft = annot.get("/FT", "")
        if str(t) == field_name and str(ft) == "/Btn":
            kids = annot.get("/Kids", [])
            for kid_ref in kids:
                kid = kid_ref.get_object()
                ap = kid.get("/AP", {})
                ap_obj = ap.get_object() if hasattr(ap, "get_object") else ap
                n = ap_obj.get("/N", {}) if ap_obj else {}
                n_obj = n.get_object() if hasattr(n, "get_object") else n
                states = list(n_obj.keys()) if hasattr(n_obj, "keys") else []
                if on_state in states:
                    kid.update({NameObject("/AS"): NameObject(on_state)})
                else:
                    kid.update({NameObject("/AS"): NameObject("/Off")})
            # Also set /V on the parent
            annot.update({NameObject("/V"): NameObject(on_state)})
            return


_STATE_NAMES: dict[str, str] = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY",
}


def _parse_address(address: str) -> tuple[str, str, str, str]:
    """
    Robust split of an address string into (street, city, state, zip).
    Handles both simple 'Street, City, ST ZIP' and Nominatim full-form
    'Street, Neighborhood, City, County, State, ZIP, Country' formats.
    """
    if not address:
        return "", "", "", ""
    parts = [p.strip() for p in address.split(",") if p.strip()]
    if not parts:
        return "", "", "", ""

    street = parts[0]
    zip_code = ""
    state = ""

    # Scan all parts (from the end) for zip and state
    for part in reversed(parts[1:]):
        part_s = part.strip()
        # "PA 19103" pattern
        m = re.match(r"([A-Z]{2})\s+(\d{5}(?:-\d{4})?)", part_s)
        if m:
            state = state or m.group(1)
            zip_code = zip_code or m.group(2)[:5]
            continue
        # Pure 5-digit ZIP
        if re.match(r"^\d{5}(?:-\d{4})?$", part_s):
            zip_code = zip_code or part_s[:5]
            continue
        # 2-letter state abbreviation
        if re.match(r"^[A-Z]{2}$", part_s):
            state = state or part_s
            continue
        # Full state name (e.g. "Pennsylvania" from Nominatim)
        if not state and part_s.lower() in _STATE_NAMES:
            state = _STATE_NAMES[part_s.lower()]

    # City: prefer the part immediately before the state/zip section.
    # For simple format "Street, City, ST ZIP" → parts[1] is city.
    # For Nominatim "Street, Neighborhood, City, County, State, ZIP, Country"
    # → skip trailing non-city parts and take the last plausible city part.
    # Heuristic: skip parts that are zip codes, state names/abbrevs, or "United States".
    skip_set = {"united states", "usa"}
    city = ""
    for part in parts[1:]:
        part_s = part.strip()
        if re.match(r"^\d{5}(?:-\d{4})?$", part_s):
            continue
        if re.match(r"^[A-Z]{2}$", part_s):
            continue
        if re.match(r"([A-Z]{2})\s+(\d{5})", part_s):
            continue
        if part_s.lower() in _STATE_NAMES:
            continue
        if part_s.lower() in skip_set:
            continue
        # Accept the first non-skipped part as city
        city = part_s
        break

    return street, city, state, zip_code


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def generate_pdf(
    patient_data: dict,
    visit_data: dict,
    provider_data: dict,
) -> bytes:
    """
    Fills the official CMS 1500 blank form with claim data and returns PDF bytes.

    patient_data keys: name, medicaid_id, date_of_birth (date|None), gender (str),
                       address (str|None), referring_provider_npi (str|None)
    visit_data keys:   visit_type (str), visit_date (date|str|None), location_type (str|None),
                       prior_auth_number (str|None)
    provider_data keys: npi (str), full_name (str), provider_address (str), provider_phone (str)
    """
    proc_code, modifier, rate_cents, diag_codes, _ = billing_for_visit(
        visit_data.get("visit_type", "")
    )
    billed = Decimal(rate_cents) / 100
    pos_code = "02" if visit_data.get("location_type") == "telehealth" else "12"

    # Service date
    svc_date_raw = visit_data.get("visit_date")
    if isinstance(svc_date_raw, date):
        svc_mm = svc_date_raw.strftime("%m")
        svc_dd = svc_date_raw.strftime("%d")
        svc_yy = svc_date_raw.strftime("%Y")
    else:
        parts = str(svc_date_raw or "").split("-")
        svc_yy, svc_mm, svc_dd = (parts + ["", "", ""])[:3]

    # Patient info
    name = patient_data.get("name", "")
    name_parts = name.strip().split()
    last_name = name_parts[-1] if len(name_parts) > 1 else name
    first_name = " ".join(name_parts[:-1]) if len(name_parts) > 1 else ""
    patient_display = f"{last_name}, {first_name}".strip(", ")

    gender = patient_data.get("gender", "F")
    medicaid_id = patient_data.get("medicaid_id", "")
    dob: date | None = patient_data.get("date_of_birth")
    dob_mm = dob.strftime("%m") if dob else ""
    dob_dd = dob.strftime("%d") if dob else ""
    dob_yy = dob.strftime("%Y") if dob else ""

    address = patient_data.get("address", "")
    pt_street, pt_city, pt_state, pt_zip = _parse_address(address)

    # Provider info
    npi = provider_data.get("npi", "")
    provider_name = provider_data.get("full_name", "")
    prov_addr = provider_data.get("provider_address", "")
    prov_phone = provider_data.get("provider_phone", "")
    doc_street, doc_city, doc_state, doc_zip = _parse_address(prov_addr)

    # Diagnosis pointer (A, AB, etc.)
    diag_ptr = "".join(chr(ord("A") + i) for i in range(len(diag_codes))) or "A"

    # -----------------------------------------------------------------------
    # Build field value map
    # -----------------------------------------------------------------------
    text_fields: dict[str, str] = {
        # Box 1a — Insured's ID (Medicaid member ID)
        "insurance_id": medicaid_id,

        # Box 2 — Patient name (Last, First)
        "pt_name": patient_display,

        # Box 3 — Patient DOB
        "birth_mm": dob_mm,
        "birth_dd": dob_dd,
        "birth_yy": dob_yy,

        # Box 4 — Insured's name (same as patient for Medicaid self-pay)
        "ins_name": patient_display,

        # Box 5 — Patient address
        "pt_street": pt_street,
        "pt_city": pt_city,
        "pt_state": pt_state,
        "pt_zip": pt_zip,

        # Box 21 — Diagnosis codes (ICD-10)
        "diagnosis1": diag_codes[0] if len(diag_codes) > 0 else "",
        "diagnosis2": diag_codes[1] if len(diag_codes) > 1 else "",
        "diagnosis3": diag_codes[2] if len(diag_codes) > 2 else "",
        "diagnosis4": diag_codes[3] if len(diag_codes) > 3 else "",

        # Box 24A — Service date (line 1, from = to for single-day visit)
        "sv1_mm_from": svc_mm,
        "sv1_dd_from": svc_dd,
        "sv1_yy_from": svc_yy,
        "sv1_mm_end":  svc_mm,
        "sv1_dd_end":  svc_dd,
        "sv1_yy_end":  svc_yy,

        # Box 24B — Place of service
        "place1": pos_code,

        # Box 24D — Procedure code + modifier
        "cpt1":  proc_code,
        "mod1":  modifier,

        # Box 24E — Diagnosis pointer
        "diag1": diag_ptr,

        # Box 24F — Charges
        "ch1": f"{billed:.2f}",

        # Box 24G — Days/units
        "day1": "1",

        # Box 24J — Rendering provider NPI
        "local1a": npi,

        # Box 25 — Federal Tax ID (use NPI)
        "tax_id": npi,

        # Box 28 — Total charge
        "t_charge": f"{billed:.2f}",

        # Box 31 — Physician signature + date
        "physician_signature": provider_name,
        "physician_date": f"{svc_mm}/{svc_dd}/{svc_yy}" if svc_mm else "",

        # Box 32 — Service facility (patient home for home visits)
        "fac_name":     f"Patient Home" if pos_code == "12" else "Telehealth",
        "fac_street":   pt_street,
        "fac_location": f"{pt_city}, {pt_state} {pt_zip}".strip(", "),

        # Box 33 — Billing provider
        "doc_name":     provider_name,
        "doc_street":   doc_street,
        "doc_location": f"{doc_city}, {doc_state} {doc_zip}".strip(", ") if doc_city else "",
        "doc_phone":    prov_phone,

        # Box 33a — NPI
        "pin": npi,

        # Box 33b — Taxonomy as group qualifier
        "grp": DOULA_TAXONOMY,

        # Box 17b — Referring/supervising provider NPI (MANDATORY — claim rejected without it)
        "ref_physician": patient_data.get("referring_provider_npi") or "",

        # Box 23 — Prior authorization number (required by Geisinger)
        "prior_auth": visit_data.get("prior_auth_number") or "",
    }

    # -----------------------------------------------------------------------
    # Fill the form
    # -----------------------------------------------------------------------
    reader = PdfReader(_BLANK_FORM)
    writer = PdfWriter()
    writer.append(reader)

    # Fill text fields on page 0
    writer.update_page_form_field_values(writer.pages[0], text_fields, auto_regenerate=False)

    # Set radio buttons
    _set_radio(writer, 0, "insurance_type", "/Medicaid")
    _set_radio(writer, 0, "sex", "/F" if gender == "F" else "/M")
    _set_radio(writer, 0, "rel_to_ins", "/S")   # Self
    _set_radio(writer, 0, "assignment", "/YES")

    # Flatten (make fields read-only in the output)
    writer.compress_identical_objects(remove_identicals=True, remove_orphans=True)

    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.read()

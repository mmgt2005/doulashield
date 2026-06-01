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

import logging

from app.core.billing_constants import DOULA_TAXONOMY, billing_for_visit

log = logging.getLogger(__name__)

_BLANK_FORM = Path(__file__).parent.parent / "static" / "cms1500_blank.pdf"


# ---------------------------------------------------------------------------
# Helpers for setting radio group values
# ---------------------------------------------------------------------------

def _set_radio(writer: PdfWriter, field_name: str, on_state: str) -> None:
    """Set a radio button group by name, walking the AcroForm /Fields tree."""
    root = writer._root_object
    acroform = root.get("/AcroForm", {})
    acroform_obj = acroform.get_object() if hasattr(acroform, "get_object") else acroform
    fields_ref = acroform_obj.get("/Fields", [])
    fields_arr = fields_ref.get_object() if hasattr(fields_ref, "get_object") else fields_ref
    for field_ref in fields_arr:
        field = field_ref.get_object() if hasattr(field_ref, "get_object") else field_ref
        if str(field.get("/T", "")) != field_name or str(field.get("/FT", "")) != "/Btn":
            continue
        field.update({NameObject("/V"): NameObject(on_state)})
        kids_ref = field.get("/Kids", None)
        if kids_ref is None:
            return
        kids = kids_ref.get_object() if hasattr(kids_ref, "get_object") else kids_ref
        for kid_ref in kids:
            kid = kid_ref.get_object() if hasattr(kid_ref, "get_object") else kid_ref
            ap = kid.get("/AP", {})
            ap_obj = ap.get_object() if hasattr(ap, "get_object") else ap
            n = ap_obj.get("/N", {}) if ap_obj else {}
            n_obj = n.get_object() if hasattr(n, "get_object") else n
            states = list(n_obj.keys()) if hasattr(n_obj, "keys") else []
            kid.update({NameObject("/AS"): NameObject(on_state if on_state in states else "/Off")})
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
    city = ""

    # Scan all parts (from the end) for zip and state
    for part in reversed(parts[1:]):
        part_s = part.strip()
        # "City ST ZIP" combined in one part — e.g. "Philadelphia PA 19103"
        m2 = re.match(r"^(.+?)\s+([A-Z]{2})\s+(\d{5}(?:-\d{4})?)$", part_s)
        if m2:
            city = city or m2.group(1).strip()
            state = state or m2.group(2)
            zip_code = zip_code or m2.group(3)
            continue
        # "PA 19103" pattern
        m = re.match(r"([A-Z]{2})\s+(\d{5}(?:-\d{4})?)", part_s)
        if m:
            state = state or m.group(1)
            zip_code = zip_code or m.group(2)
            continue
        # Pure 5-digit ZIP
        if re.match(r"^\d{5}(?:-\d{4})?$", part_s):
            zip_code = zip_code or part_s
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
    for part in parts[1:]:
        part_s = part.strip()
        if re.match(r"^\d{5}(?:-\d{4})?$", part_s):
            continue
        if re.match(r"^[A-Z]{2}$", part_s):
            continue
        if re.match(r"([A-Z]{2})\s+(\d{5})", part_s):
            continue
        if re.match(r"^.+?\s+[A-Z]{2}\s+\d{5}", part_s):
            # "City ST ZIP" combined — city already extracted in the reverse scan above
            break
        if part_s.lower() in _STATE_NAMES:
            continue
        if part_s.lower() in skip_set:
            continue
        # Accept the first non-skipped part as city
        city = part_s
        break

    return street, city, state, zip_code


def _overlay_signature(pdf_bytes: bytes, sig_bytes: bytes, x: float, y: float, max_w: float, max_h: float) -> bytes:
    """
    Overlay a PNG signature image onto a PDF page at the given coordinates.
    Returns merged PDF bytes, or original bytes unchanged if overlay fails.
    x, y = bottom-left corner in points (letter page 612×792 pts from bottom-left).
    """
    try:
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib.pagesizes import letter
        from PIL import Image as PILImage

        img = PILImage.open(io.BytesIO(sig_bytes)).convert("RGBA")
        img_w, img_h = img.size
        scale = min(max_w / img_w, max_h / img_h)
        draw_w = img_w * scale
        draw_h = img_h * scale

        overlay_buf = io.BytesIO()
        c = rl_canvas.Canvas(overlay_buf, pagesize=letter)
        c.drawInlineImage(img, x, y, width=draw_w, height=draw_h)
        c.save()
        overlay_buf.seek(0)

        base_reader = PdfReader(io.BytesIO(pdf_bytes))
        overlay_reader = PdfReader(overlay_buf)
        merge_writer = PdfWriter()
        pg = base_reader.pages[0]
        pg.merge_page(overlay_reader.pages[0])
        merge_writer.add_page(pg)
        out = io.BytesIO()
        merge_writer.write(out)
        out.seek(0)
        return out.read()
    except Exception as exc:
        log.warning("Signature overlay failed: %s", exc)
        return pdf_bytes


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
                       address (str|None), mco (str|None),
                       referring_provider_npi (str|None), referring_provider_name (str|None),
                       has_other_insurance (bool), ma91_signed_at (datetime|None),
                       ma91_signature_bytes (bytes|None)
    visit_data keys:   visit_type (str), visit_date (date|str|None), location_type (str|None),
                       prior_auth_number (str|None), alternate_location (str|None)
    provider_data keys: npi (str), full_name (str), provider_address (str), provider_phone (str),
                        provider_ssn (str), provider_signature_bytes (bytes|None)
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
    prov_phone_raw = provider_data.get("provider_phone", "")
    prov_phone_digits = re.sub(r"\D", "", prov_phone_raw)
    prov_phone_area = prov_phone_digits[:3] if len(prov_phone_digits) >= 10 else ""
    prov_phone_num = prov_phone_digits[3:] if len(prov_phone_digits) >= 10 else prov_phone_digits
    doc_street, doc_city, doc_state, doc_zip = _parse_address(prov_addr)

    provider_ssn = provider_data.get("provider_ssn", "")

    # MA 91 date for Box 12
    ma91_signed_at = patient_data.get("ma91_signed_at")
    if ma91_signed_at:
        try:
            ma91_date_str = ma91_signed_at.strftime("%m/%d/%Y")
        except AttributeError:
            ma91_date_str = str(ma91_signed_at)[:10]
    else:
        ma91_date_str = ""

    # Signature bytes — checked early so text fields are set correctly below
    ma91_sig_bytes: bytes | None = patient_data.get("ma91_signature_bytes")
    provider_sig_bytes: bytes | None = provider_data.get("provider_signature_bytes")

    # Diagnosis pointer (A, AB, etc.)
    diag_ptr = "".join(chr(ord("A") + i) for i in range(len(diag_codes))) or "A"

    # Box 32 facility name
    alternate_location = visit_data.get("alternate_location") or ""
    if alternate_location:
        fac_name = alternate_location
    elif pos_code == "12":
        fac_name = "Patient Home"
    else:
        fac_name = "Telehealth"

    # Box 26 patient account number
    pt_account = medicaid_id[-8:] if len(medicaid_id) >= 8 else medicaid_id

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

        # Box 7 — Insured's address (same as patient for Medicaid self-pay)
        "ins_street": pt_street,
        "ins_city": pt_city,
        "ins_state": pt_state,
        "ins_zip": pt_zip,

        # Box 11 — Insured's Policy/Group Number (use card's group number if available, else Medicaid ID)
        "ins_policy": patient_data.get("policy_group") or medicaid_id,

        # Box 11a — Insured DOB (mirrors patient for self-pay)
        "ins_dob_mm": dob_mm,
        "ins_dob_dd": dob_dd,
        "ins_dob_yy": dob_yy,

        # Box 11c — Insurance plan / MCO name
        "insurance_name": patient_data.get("mco") or "",

        # Box 12 — Patient signature + MA 91 date
        # Provider signs here (same image as Box 31); clear text when image is available
        "pt_signature": "" if provider_sig_bytes else provider_name,
        "pt_date": ma91_date_str,

        # Box 13 — Client/patient MA 91 signature (authorization to assign benefits)
        # Clear text field when actual image is available so it shows through
        "ins_signature": "" if ma91_sig_bytes else "Signature on File",

        # Box 17 — Referring provider NAME (not NPI — field is ref_physician)
        "ref_physician": patient_data.get("referring_provider_name") or "",

        # Box 17b — Referring provider NPI (field is id_physician)
        "id_physician": patient_data.get("referring_provider_npi") or "",

        # Box 21 — Diagnosis codes (ICD-10)
        "diagnosis1": diag_codes[0] if len(diag_codes) > 0 else "",
        "diagnosis2": diag_codes[1] if len(diag_codes) > 1 else "",
        "diagnosis3": diag_codes[2] if len(diag_codes) > 2 else "",
        "diagnosis4": diag_codes[3] if len(diag_codes) > 3 else "",

        # Box 23 — Prior authorization number (Geisinger requires it)
        "prior_auth": visit_data.get("prior_auth_number") or "",

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

        # Box 24I — Qualifier ("1" = NPI); Box 24J — Rendering provider NPI
        "local1a": "1",
        "local1":  npi,

        # Box 25 — Federal Tax ID (SSN for sole proprietor)
        "tax_id": provider_ssn,

        # Box 26 — Patient account number
        "pt_account": pt_account,

        # Box 28 — Total charge
        "t_charge": f"{billed:.2f}",

        # Box 31 — Physician signature + date
        # Clear text field when actual image is available so it shows through
        "physician_signature": "" if provider_sig_bytes else provider_name,
        "physician_date": f"{svc_mm}/{svc_dd}/{svc_yy}" if svc_mm else "",

        # Box 32 — Service facility
        "fac_name":     fac_name,
        "fac_street":   pt_street,
        "fac_location": f"{pt_city}, {pt_state} {pt_zip}".strip(", "),

        # Box 33 — Billing provider
        "doc_name":       provider_name,
        "doc_street":     doc_street,
        "doc_location":   f"{doc_city}, {doc_state} {doc_zip}".strip(", ") if doc_city else "",
        "doc_phone area": prov_phone_area,
        "doc_phone":      prov_phone_num,

        # Box 33a — NPI
        "pin": npi,

        # Box 33b — Taxonomy as group qualifier
        "grp": DOULA_TAXONOMY,
    }

    # -----------------------------------------------------------------------
    # Fill the form
    # -----------------------------------------------------------------------
    reader = PdfReader(_BLANK_FORM)
    writer = PdfWriter()
    writer.append(reader)

    writer.update_page_form_field_values(writer.pages[0], text_fields, auto_regenerate=False)

    # Radio buttons
    _set_radio(writer, "insurance_type", "/Medicaid")
    _set_radio(writer, "sex", "/F" if gender == "F" else "/M")
    _set_radio(writer, "ins_sex", "/FEMALE" if gender == "F" else "/MALE")
    _set_radio(writer, "rel_to_ins", "/S")    # Self
    _set_radio(writer, "assignment", "/YES")
    _set_radio(writer, "ssn", "/SSN")         # Box 25 — SSN not EIN
    _set_radio(writer, "ins_benefit_plan", "/YES" if patient_data.get("has_other_insurance") else "/NO")

    writer.compress_identical_objects(remove_identicals=True, remove_orphans=True)

    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    pdf_bytes = buf.read()

    # -----------------------------------------------------------------------
    # Overlay signature images at AcroForm field positions (bottom-left origin)
    # Box 12 pt_signature:        rect=[55.99,  412.79, 236.15, 424.79]  — provider sig
    # Box 13 ins_signature:       rect=[412.35, 412.79, 584.94, 424.79]  — client MA 91 sig
    # Box 31 physician_signature: rect=[19.88,   53.88, 175.87,  65.88]  — provider sig
    # -----------------------------------------------------------------------
    if provider_sig_bytes:
        pdf_bytes = _overlay_signature(pdf_bytes, provider_sig_bytes, 56, 410, 180, 25)
    if ma91_sig_bytes:
        pdf_bytes = _overlay_signature(pdf_bytes, ma91_sig_bytes, 412, 410, 173, 25)
    if provider_sig_bytes:
        pdf_bytes = _overlay_signature(pdf_bytes, provider_sig_bytes, 20, 50, 156, 25)

    return pdf_bytes

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import uuid
from datetime import datetime, timezone

import anthropic
import httpx
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)

_MAX_IMAGE_SIDE = 1568  # Anthropic recommended max longest side


def _resize_image(data: bytes, content_type: str) -> tuple[bytes, str]:
    """Downscale an image so its longest side is at most _MAX_IMAGE_SIDE pixels."""
    img = Image.open(io.BytesIO(data))
    w, h = img.size
    if max(w, h) > _MAX_IMAGE_SIDE:
        scale = _MAX_IMAGE_SIDE / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        buf = io.BytesIO()
        fmt = "JPEG" if content_type == "image/jpeg" else "PNG"
        if img.mode in ("RGBA", "P") and fmt == "JPEG":
            img = img.convert("RGB")
        img.save(buf, format=fmt, quality=85)
        logger.info("Image resized from %dx%d to %dx%d", w, h, int(w * scale), int(h * scale))
        return buf.getvalue(), content_type
    return data, content_type


_PROMPTS: dict[str, str] = {
    "medicaid_card": (
        "Extract information from this Medicaid card image and return ONLY valid JSON with no commentary:\n"
        '{"name": "full patient name as printed", "medicaid_id": "member or beneficiary ID", '
        '"date_of_birth": "member date of birth in YYYY-MM-DD format or null", '
        '"policy_group": "group number, plan group, or policy group printed on the card or null", '
        '"mco": "normalize to exactly one of these Pennsylvania MCO names: '
        "AmeriHealth Caritas, Keystone First, UPMC For You, Geisinger Health Plan, Health Partners Plans, "
        "Aetna Better Health, UnitedHealthcare Community Plan, Highmark Wholecare, FFS. "
        "Map known aliases: Gateway Health → Highmark Wholecare; HPP → Health Partners Plans. "
        "Keystone First is a separate MCO from AmeriHealth Caritas — do NOT merge them. "
        'Use FFS if the card shows fee-for-service or no MCO is identifiable.", '
        '"address": "beneficiary street address if printed or null"}\n'
        "Use null for any field you cannot read clearly."
    ),
    "soap_note": (
        "This is a handwritten SOAP note page from a doula's client care handbook.\n"
        "The page has four clearly labeled sections: SUBJECTIVE, OBJECTIVE, ASSESSMENT, "
        "and PLAN (which may also appear as PLAN / NEXT STEPS — both map to the 'plan' field).\n"
        "SUBJECTIVE and OBJECTIVE appear side-by-side in two columns; "
        "ASSESSMENT and PLAN appear below as full-width sections.\n"
        "Each section has a colored heading above ruled writing lines where the doula writes by hand.\n"
        "The page header may include an appointment date, client name, date of birth, and MCO/insurance — "
        "extract the appointment date as visit_date if present.\n"
        "Return ONLY valid JSON with no commentary:\n"
        '{"visit_date": "YYYY-MM-DD or null", "subjective": "handwritten text or null", '
        '"objective": "handwritten text or null", "assessment": "handwritten text or null", '
        '"plan": "handwritten text or null", '
        '"next_appointment_date": "YYYY-MM-DD from the Next Appointment Date footer line or null"}\n'
        "Use null for any section that is blank or whose handwriting you cannot read clearly."
    ),
    "prenatal": (
        "This is a handwritten prenatal or postnatal visit log page from a doula's client care handbook.\n"
        "The page header may include the client's name, address, and date of birth — extract those too if present.\n"
        "Return ONLY valid JSON with no commentary:\n"
        '{"log_type": "prenatal or postnatal", "entry_date": "YYYY-MM-DD or null", '
        '"entry": "all visit notes combined into a single text block", '
        '"address": "client street address from header or null", '
        '"date_of_birth": "client date of birth in YYYY-MM-DD format from header or null"}'
    ),
    "birth": (
        "This is a handwritten birth log page from a doula's client care handbook.\n"
        "Return ONLY valid JSON with no commentary:\n"
        '{"birth_date": "YYYY-MM-DD or null", "birth_time": "HH:MM 24-hour format or null", '
        '"birth_location": "location text or null", "notes": "additional notes or null"}'
    ),
    "ma_589": (
        "This is a Pennsylvania MA 589 Medical Assistance Physician Certification form.\n"
        "Extract the referring physician information and return ONLY valid JSON with no commentary:\n"
        '{"referring_provider_name": "physician full name as printed or null", '
        '"referring_provider_npi": "10-digit NPI number or null"}\n'
        "Use null for any field you cannot read clearly."
    ),
    "access_card": (
        "This is a Pennsylvania ACCESS card (the EBT-style Medicaid benefits card issued by PA DHS).\n"
        "Extract the cardholder information and return ONLY valid JSON with no commentary:\n"
        '{"medicaid_id": "the recipient ID or card number printed on the card", '
        '"name": "cardholder name as printed or null"}\n'
        "Use null for any field you cannot read clearly."
    ),
    "remittance_eob": (
        "Extract ALL claim payment lines from this insurance Explanation of Benefits (EOB) "
        "or remittance advice document and return ONLY valid JSON with no commentary:\n"
        '{"check_number": "check or EFT number or null", '
        '"payment_date": "YYYY-MM-DD or null", '
        '"total_paid": "total payment amount as a number string or null", '
        '"claims": ['
        '{"patient_name": "patient full name as printed or null", '
        '"service_date": "YYYY-MM-DD or null", '
        '"procedure_code": "CPT or HCPCS code or null", '
        '"billed_amount": "billed amount as a number string or null", '
        '"paid_amount": "paid amount as a number string or null", '
        '"status": "paid or denied or adjusted", '
        '"denial_reason": "denial codes and descriptions or null"}]}\n'
        "IMPORTANT: Extract EVERY claim line in the document — do not stop after the first. "
        "For status: paid=payment >$0 with no denial codes; denied=$0 payment with denial codes; "
        "adjusted=partial payment or adjustment codes present. "
        "For denial_reason include codes and descriptions "
        "(e.g. 'CO-45: Charge exceeds fee schedule; CO-97: Bundled service'). "
        "Use null for any field you cannot read clearly."
    ),
}


_SOAP_TRANSLATE_PROMPT = (
    "You are a professional clinical scribe specializing in perinatal health and Medicaid "
    "documentation for Pennsylvania Type 13 doula services.\n"
    "Translate the plain-language doula notes below into professional clinical SOAP format "
    "suitable for insurance audit. Constraints:\n"
    "1. Do NOT hallucinate — only use information present in the input. Never invent clinical details.\n"
    "2. Use objective, concise clinical language. Replace informal terms with professional equivalents "
    "(e.g., 'really tired' → 'reports increased fatigue'; 'scared' → 'expresses anxiety regarding').\n"
    "3. Do not use ICD-10 O-codes. Permitted: Z-codes and general health status language.\n"
    "4. If a section input is empty or 'Not provided', return null for that field.\n"
    "5. Ensure the note supports billing justification for T1032/T1033.\n"
    "Return ONLY valid JSON with no commentary:\n"
    '{{"subjective": "translated text or null", "objective": "translated text or null", '
    '"assessment": "translated text or null", "plan": "translated text or null"}}\n\n'
    "Input:\n"
    "Subjective: {subjective}\n"
    "Objective: {objective}\n"
    "Assessment: {assessment}\n"
    "Plan: {plan}"
)


def _run_soap_translate(inputs: dict) -> dict:
    subj = inputs.get("subjective") or "Not provided"
    obj = inputs.get("objective") or "Not provided"
    asmt = inputs.get("assessment") or "Not provided"
    plan = inputs.get("plan") or "Not provided"

    prompt = _SOAP_TRANSLATE_PROMPT.format(
        subjective=subj, objective=obj, assessment=asmt, plan=plan
    )
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    try:
        msg = client.messages.create(
            model="claude-haiku-5-5",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.AuthenticationError as exc:
        logger.error("Anthropic auth failure (check ANTHROPIC_API_KEY): %s", exc)
        raise ValueError("Anthropic authentication failed — check API key") from exc
    except anthropic.BadRequestError as exc:
        logger.error("Anthropic 400 (SOAP translate): %s", exc)
        raise ValueError("Translation request rejected") from exc

    text_block = next((b for b in msg.content if hasattr(b, "text")), None)
    if text_block is None:
        raise ValueError("Claude returned no text in response")
    raw = text_block.text.strip()
    logger.debug("Claude SOAP translate raw (first 200 chars): %s", raw[:200])
    start = raw.find('{')
    end = raw.rfind('}')
    if start != -1 and end != -1 and end > start:
        raw = raw[start:end + 1]
    elif raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


async def translate_soap(inputs: dict) -> dict:
    """Call Claude Haiku to translate plain-language SOAP notes into clinical format."""
    try:
        return await asyncio.to_thread(_run_soap_translate, inputs)
    except ValueError:
        raise
    except (json.JSONDecodeError, KeyError, IndexError, Exception) as exc:
        logger.error("SOAP translation failed: %s", exc)
        raise ValueError("SOAP translation failed") from exc


def _run_claude(image_bytes: bytes, content_type: str, page_type: str) -> dict:
    if not image_bytes:
        raise ValueError("Empty file data received — file may not have uploaded correctly")

    logger.info("OCR request: size=%d bytes, content_type=%s, page_type=%s",
                len(image_bytes), content_type, page_type)

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    is_pdf = content_type == "application/pdf"

    if is_pdf:
        # Extract text from the PDF with pypdf (digital EOBs are always text-based).
        # This is cheaper, model-agnostic, and avoids the Anthropic PDF beta API.
        from pypdf import PdfReader
        try:
            reader = PdfReader(io.BytesIO(image_bytes))
            page_texts = [p.extract_text() or "" for p in reader.pages]
            pdf_text = "\n\n".join(t for t in page_texts if t.strip())
        except Exception as exc:
            logger.error("pypdf extraction failed: %s", exc)
            raise ValueError("Could not read PDF — file may be corrupted or password-protected") from exc

        if not pdf_text.strip():
            raise ValueError("PDF contains no extractable text — scanned image PDFs are not supported for EOB scanning")

        logger.info("PDF text extracted: %d chars from %d pages", len(pdf_text), len(reader.pages))

        prompt = _PROMPTS[page_type] + "\n\nDocument text:\n" + pdf_text
        try:
            msg = client.messages.create(
                model="claude-haiku-5-5",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.AuthenticationError as exc:
            logger.error("Anthropic auth failure (check ANTHROPIC_API_KEY): %s", exc)
            raise ValueError("Anthropic authentication failed — check API key") from exc
        except anthropic.BadRequestError as exc:
            logger.error("Anthropic 400 (PDF text): %s", exc)
            raise ValueError("Anthropic rejected the PDF text request") from exc
    else:
        image_bytes, content_type = _resize_image(image_bytes, content_type)
        b64 = base64.standard_b64encode(image_bytes).decode()
        try:
            msg = client.messages.create(
                model="claude-haiku-5-5",
                max_tokens=2048,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": content_type,
                                    "data": b64,
                                },
                            },
                            {"type": "text", "text": _PROMPTS[page_type]},
                        ],
                    }
                ],
            )
        except anthropic.AuthenticationError as exc:
            logger.error("Anthropic auth failure (check ANTHROPIC_API_KEY): %s", exc)
            raise ValueError("Anthropic authentication failed — check API key") from exc
        except anthropic.BadRequestError as exc:
            logger.error("Anthropic 400: %s", exc)
            raise ValueError("Anthropic rejected the image request") from exc

    # claude-haiku-5-5 may return a ThinkingBlock before the TextBlock; find the first text block
    text_block = next((b for b in msg.content if hasattr(b, "text")), None)
    if text_block is None:
        raise ValueError("Claude returned no text in response")
    raw = text_block.text.strip()
    logger.debug("Claude raw response (first 200 chars): %s", raw[:200])
    # Extract outermost JSON object even when Claude wraps it in prose or code fences
    start = raw.find('{')
    end = raw.rfind('}')
    if start != -1 and end != -1 and end > start:
        raw = raw[start:end + 1]
    elif raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


async def extract_image(image_bytes: bytes, content_type: str, page_type: str) -> dict:
    """Call Claude Haiku vision to extract structured data from an image."""
    try:
        return await asyncio.to_thread(_run_claude, image_bytes, content_type, page_type)
    except ValueError:
        raise
    except (json.JSONDecodeError, KeyError, IndexError, Exception) as exc:
        logger.error("OCR extraction failed: %s", exc)
        raise ValueError("Could not extract information from image") from exc


async def store_image(
    image_bytes: bytes,
    content_type: str,
    patient_id: uuid.UUID | None,
    user_id: uuid.UUID,
    label: str,
) -> str:
    """Upload image to Supabase Storage and return the storage object path."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    if "jpeg" in content_type:
        ext = "jpg"
    elif "pdf" in content_type:
        ext = "pdf"
    else:
        ext = "png"

    if patient_id:
        path = f"clients/{patient_id}/{label}-{timestamp}.{ext}"
    else:
        path = f"staging/{user_id}/{label}-{timestamp}.{ext}"

    upload_url = (
        f"{settings.SUPABASE_URL}/storage/v1/object/"
        f"{settings.SUPABASE_STORAGE_BUCKET}/{path}"
    )

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            upload_url,
            content=image_bytes,
            headers={
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                "Content-Type": content_type,
            },
        )
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Storage upload failed ({resp.status_code}): {resp.text}")

    return path


async def delete_file(path: str) -> None:
    """Delete a file from Supabase Storage."""
    delete_url = (
        f"{settings.SUPABASE_URL}/storage/v1/object/"
        f"{settings.SUPABASE_STORAGE_BUCKET}/{path}"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.delete(
            delete_url,
            headers={"Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}"},
        )
        if resp.status_code not in (200, 204):
            raise RuntimeError(f"Storage delete failed ({resp.status_code}): {resp.text}")


async def get_signed_url(path: str, expires_in: int = 60) -> str:
    """Return a short-lived signed URL for a stored image."""
    sign_url = (
        f"{settings.SUPABASE_URL}/storage/v1/object/sign/"
        f"{settings.SUPABASE_STORAGE_BUCKET}/{path}"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            sign_url,
            json={"expiresIn": expires_in},
            headers={"Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}"},
        )
        resp.raise_for_status()
        data = resp.json()
        signed_path = data["signedURL"]
        return f"{settings.SUPABASE_URL}/storage/v1{signed_path}"

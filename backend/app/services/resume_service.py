import asyncio
import json
import logging
import re

import anthropic

from app.core.config import settings

log = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are an expert healthcare credentialing specialist and professional CV writer. "
    "A doula is applying for Pennsylvania Medicaid PROMISe™ enrollment (Provider Type 13) "
    "and commercial Managed Care Organization (MCO) contracts. "
    "Transform the provider's raw notes into a complete, MCO-compliant Curriculum Vitae.\n\n"
    "OUTPUT — return ONLY valid JSON (no markdown, no prose, no code fences):\n"
    "{\n"
    '  "credentials_line": "Formatted name + credential abbreviations line, e.g. Maria Gonzalez, CPD | NPI: XXXXXXXXXX",\n'
    '  "professional_summary": "3-4 sentence summary emphasizing PA Medicaid / MCO eligibility, years of experience, specializations",\n'
    '  "certifications": [\n'
    '    {"name": "Full cert name", "issuer": "Issuing organization", "date": "Month YYYY or YYYY", "expires": "Month YYYY or null"}\n'
    "  ],\n"
    '  "experience": [\n'
    "    {\n"
    '      "start_date": "MM/YYYY",\n'
    '      "end_date": "MM/YYYY or Present",\n'
    '      "employer": "Organization or Self-Employed / Independent Doula",\n'
    '      "location": "City, State",\n'
    '      "title": "Official title or role",\n'
    '      "duties": "2-3 sentence description using clinical action verbs: Provided, Coordinated, Advocated, Documented, etc."\n'
    "    }\n"
    "  ],\n"
    '  "education": [\n'
    '    {"program": "Training or degree name", "institution": "School or org", "year": "YYYY", "hours": "number as string or null"}\n'
    "  ],\n"
    '  "skills": ["Skill 1", "Skill 2"],\n'
    '  "philosophy": "2-3 sentence philosophy of care statement in first person, professional tone"\n'
    "}\n\n"
    "Rules:\n"
    "- Experience entries in reverse chronological order (most recent first)\n"
    "- Credentials line: use name exactly as given, append credential abbreviations (CPD, PCB, etc.)\n"
    "- If no NPI is given, omit it from credentials_line\n"
    "- Professional summary must mention PA Medicaid Provider Type 13 eligibility\n"
    "- Certifications: separate CPR, HIPAA, and doula-specific certs into their own entries\n"
    "- Skills should include: HIPAA Compliance, CMS-1500 Billing, ICD-10 Coding, Availity Portal, "
    "any specializations mentioned (trauma-informed care, LGBTQ+ affirming, etc.)\n"
    "- Keep experience duties concise but include client volume when mentioned\n"
    "- If any field is unknown, use a professional placeholder (e.g. 'Dates available upon request')\n"
    "- Philosophy must be in first person, professional, not casual"
)


async def process_resume(
    name: str,
    certs: str,
    history: str,
    philosophy: str,
) -> dict:
    """Call Claude to generate a structured MCO-compliant CV from provider inputs."""
    if not settings.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY is not configured")

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    user_content = (
        f"PROVIDER NAME & CREDENTIALS:\n{name.strip() or 'Not provided'}\n\n"
        f"CERTIFICATIONS & TRAINING:\n{certs.strip() or 'Not provided'}\n\n"
        f"PROFESSIONAL HISTORY & TIMELINE NOTES:\n{history.strip() or 'Not provided'}\n\n"
        f"PHILOSOPHY OF CARE:\n{philosophy.strip() or 'Not provided'}"
    )

    def _call() -> anthropic.types.Message:
        return client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=3000,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )

    message = await asyncio.to_thread(_call)
    raw = message.content[0].text.strip()

    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        log.warning("Resume Claude response was not valid JSON: %.200s", raw)
        raise ValueError(f"AI did not return valid JSON: {exc}") from exc

    for field in ("credentials_line", "professional_summary", "experience"):
        if field not in result:
            raise ValueError(f"AI response missing required field '{field}'")

    result.setdefault("certifications", [])
    result.setdefault("education", [])
    result.setdefault("skills", [])
    result.setdefault("philosophy", "")

    return result

import asyncio
import json
import logging
import re

import anthropic

from app.core.config import settings

log = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are an expert healthcare credentialing specialist. "
    "A doula provider is applying for Pennsylvania Medicaid PROMISe™ enrollment (Provider Type 13 — Certified Perinatal Doula) "
    "and commercial Managed Care Organization (MCO) contracts. "
    "The application requires a continuous, professional, month-by-month 5-year work history. "
    "Any gap greater than 30 days between entries must be accounted for in a separate Gap Log.\n\n"
    "Take the provider's raw, unformatted notes and transform them into a compliant document.\n\n"
    "OUTPUT — return ONLY valid JSON (no markdown, no prose, no code fences):\n"
    "{\n"
    '  "rows": [\n'
    "    {\n"
    '      "start_date": "MM/YYYY",\n'
    '      "end_date": "MM/YYYY or Present",\n'
    '      "employer_name": "Organization or Self-Employed",\n'
    '      "address": "City, State (full address if provided)",\n'
    '      "job_title": "Title or Role",\n'
    '      "duties": "1-2 sentence description using clinical/administrative action verbs"\n'
    "    }\n"
    "  ],\n"
    '  "gaps": [\n'
    "    {\n"
    '      "start_date": "MM/YYYY",\n'
    '      "end_date": "MM/YYYY",\n'
    '      "duration_days": 45,\n'
    '      "explanation": "Standard administrative explanation for the gap period"\n'
    "    }\n"
    "  ]\n"
    "}\n\n"
    "Rules:\n"
    "- List entries in reverse chronological order (most recent first)\n"
    "- Cover the last 5 years from today\n"
    "- If a date is vague (e.g. 'last summer'), estimate the most likely MM/YYYY\n"
    "- For self-employment or gig work, use 'Self-Employed / Independent Doula' as employer_name\n"
    "- For volunteer work, include it — it counts for credentialing\n"
    "- Only include gaps LONGER than 30 days between any two consecutive entries\n"
    "- If there are no gaps, return an empty gaps array\n"
    "- Keep duties to 1-2 sentences using action verbs like 'Provided,' 'Managed,' 'Coordinated,' "
    "'Maintained,' 'Delivered,' 'Supported'\n"
    "- If the provider gives an address, include it; otherwise use City, State\n"
    "- If a gap has a clear reason (family care, sabbatical, education), note it professionally"
)


async def process_work_history(brain_dump: str) -> dict:
    """Call Claude to transform freeform work history notes into structured rows + gap log."""
    if not settings.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY is not configured")

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def _call() -> anthropic.types.Message:
        return client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": brain_dump.strip()}],
        )

    message = await asyncio.to_thread(_call)
    raw = message.content[0].text.strip()

    # Strip markdown code fences if the model adds them despite instructions
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        log.warning("Work history Claude response was not valid JSON: %.200s", raw)
        raise ValueError(f"AI did not return valid JSON: {exc}") from exc

    if "rows" not in result or not isinstance(result["rows"], list):
        raise ValueError("AI response missing 'rows' list")
    result.setdefault("gaps", [])

    return result

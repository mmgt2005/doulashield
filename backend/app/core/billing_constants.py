from decimal import Decimal

DOULA_TAXONOMY = "374J00000X"
PROVIDER_TYPE = "13"
SPECIALTY_CODE = "130"

# Submission channel for each MCO: 'availity' | 'uhc' | 'manual'
MCO_SUBMISSION_CHANNEL: dict[str, str] = {
    "AmeriHealth Caritas": "availity",
    "Keystone First": "availity",
    "Geisinger Health Plan": "availity",
    "Highmark Wholecare": "availity",
    "Aetna Better Health": "availity",
    "UnitedHealthcare Community Plan": "uhc",
    "UPMC For You": "manual",
    "Health Partners Plans": "manual",
    "FFS": "manual",
}

# Portal links for manual MCOs (shown when provider must submit outside the app)
MCO_PORTAL_LINKS: dict[str, dict[str, str]] = {
    "UPMC For You": {
        "name": "UPMC Health Plan Provider Portal",
        "url": "https://www.upmchealthplan.com/providers/",
    },
    "Health Partners Plans": {
        "name": "HPPServe (via Change Healthcare / Emdeon)",
        "url": "https://www.healthpartnersplans.com/providers/",
    },
    "FFS": {
        "name": "PROMISe™ Provider Portal (PA DHS)",
        "url": "https://promise.dpw.state.pa.us/",
    },
}

# visit_type prefix → (procedure_code, modifier, rate_cents, default_diag_codes, clinical_note)
VISIT_BILLING: dict[str, tuple[str, str, int, list[str], str]] = {
    "prenatal":    ("T1032", "U7", 10000,  ["Z32.2"], "Document topics/support provided"),
    "postnatal":   ("T1032", "U8", 10000,  ["Z39.1"], "Document physical/emotional recovery"),
    "labor":       ("T1033", "",  100000,  ["Z33.1"],           "One per pregnancy — include time-in/out"),
    "crisis_loss": ("T1032", "U9", 17500,  ["Z39.2"],           "Capped at 2 per year"),
}


def billing_for_visit(visit_type: str) -> tuple[str, str, int, list[str], str]:
    """Returns (procedure_code, modifier, rate_cents, diag_codes, clinical_note)."""
    if visit_type == "labor":
        return VISIT_BILLING["labor"]
    if visit_type.startswith("prenatal"):
        return VISIT_BILLING["prenatal"]
    if visit_type.startswith("postnatal"):
        return VISIT_BILLING["postnatal"]
    return VISIT_BILLING["crisis_loss"]


def rate_dollars(visit_type: str) -> Decimal:
    _, _, cents, _, _ = billing_for_visit(visit_type)
    return Decimal(cents) / 100

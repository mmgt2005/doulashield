import logging
import re
import time
from typing import Optional

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)

_TOKEN_URL = "https://apis.usps.com/oauth2/v3/token"
_ADDRESS_URL = "https://apis.usps.com/addresses/v3/address"

# Module-level token cache: (token_str, expiry_monotonic)
_token_cache: tuple[str, float] | None = None


async def _get_token(client: httpx.AsyncClient) -> str | None:
    """Return a valid OAuth2 Bearer token, refreshing when expired."""
    global _token_cache

    if _token_cache:
        token, expiry = _token_cache
        if time.monotonic() < expiry:
            return token

    if not settings.USPS_CLIENT_ID or not settings.USPS_CLIENT_SECRET:
        return None

    try:
        resp = await client.post(
            _TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": settings.USPS_CLIENT_ID,
                "client_secret": settings.USPS_CLIENT_SECRET,
            },
            timeout=5.0,
        )
        if resp.status_code != 200:
            log.warning("USPS token HTTP %s: %s", resp.status_code, resp.text[:200])
            return None
        data = resp.json()
        token = data.get("access_token", "")
        expires_in = int(data.get("expires_in", 28800))  # default 8 hours
        _token_cache = (token, time.monotonic() + expires_in - 60)
        return token or None
    except Exception as exc:
        log.warning("USPS token fetch error: %s", exc)
        return None


def _parse_for_usps(address: str) -> tuple[str, str, str, str]:
    """Parse 'Street, City, ST ZIP' into (street, city, state, zip5).

    Returns empty strings for any part that cannot be determined.
    """
    parts = [p.strip() for p in address.split(",") if p.strip()]
    if not parts:
        return ("", "", "", "")

    street = parts[0]
    city = ""
    state = ""
    zip5 = ""

    for part in reversed(parts[1:]):
        part_s = part.strip()

        # "ST ZIP" or "City ST ZIP" — e.g. "GA 30236" or "Jonesboro GA 30236"
        m = re.match(r"^(.*\s+)?([A-Z]{2})\s+(\d{5})(?:-\d{4})?$", part_s)
        if m:
            if m.group(1) and not city:
                city = m.group(1).strip()
            if not state:
                state = m.group(2)
            if not zip5:
                zip5 = m.group(3)
            continue

        if not city:
            city = part_s

    return street, city, state, zip5


async def lookup_zip4(address: str, client: httpx.AsyncClient) -> Optional[str]:
    """Return authoritative ZIP+4 string (e.g. '30236-1234') from USPS v3 API.

    Returns None when credentials are not configured, the address cannot be
    parsed into components, or USPS cannot match the address.
    """
    if not settings.USPS_CLIENT_ID or not settings.USPS_CLIENT_SECRET or not address:
        return None

    token = await _get_token(client)
    if not token:
        return None

    street, city, state, zip5 = _parse_for_usps(address)
    if not street:
        return None

    params: dict[str, str] = {"streetAddress": street}
    if city:
        params["city"] = city
    if state:
        params["state"] = state
    if zip5:
        params["ZIPCode"] = zip5

    try:
        resp = await client.get(
            _ADDRESS_URL,
            params=params,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=5.0,
        )
        if resp.status_code != 200:
            log.info("USPS ZIP+4 HTTP %s for %r", resp.status_code, address[:60])
            return None

        data = resp.json()
        addr = data.get("address", {})
        zip_code = (addr.get("ZIPCode") or "").strip()
        zip_plus4 = (addr.get("ZIPPlus4") or "").strip()

        if zip_code and zip_plus4 and zip_plus4 not in ("", "0000"):
            result = f"{zip_code}-{zip_plus4}"
            log.info("USPS ZIP+4 %r → %s", address[:60], result)
            return result

        return None
    except Exception as exc:
        log.warning("USPS ZIP+4 error for %r: %s", address[:60], exc)
        return None


def substitute_zip4(address: str, full_zip4: str) -> str:
    """Replace a bare 5-digit ZIP in *address* with *full_zip4* ('NNNNN-NNNN').

    Only replaces the first occurrence that is not already in ZIP+4 form.
    """
    zip5 = full_zip4[:5]
    return re.sub(
        r"\b" + re.escape(zip5) + r"\b(?!-\d{4})",
        full_zip4,
        address,
        count=1,
    )

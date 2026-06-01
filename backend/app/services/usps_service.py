import logging
import re
import xml.etree.ElementTree as ET
from typing import Optional

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)

_USPS_URL = "https://secure.shippingapis.com/ShippingAPI.dll"


def _parse_for_usps(address: str) -> tuple[str, str, str, str]:
    """Parse 'Street, City, ST ZIP' into (street, city, state, zip5).

    Returns empty strings for any part that cannot be determined.
    USPS Address2 = primary street line; Address1 = apt/unit (kept blank).
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

        # "ST ZIP" or "City ST ZIP" combined — e.g. "GA 30236" or "Jonesboro GA 30236"
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
    """Return the authoritative ZIP+4 string (e.g. '30236-1234') from USPS.

    Returns None when USPS_USER_ID is not configured, the address cannot be
    parsed into components, or USPS cannot match the address.  Only the ZIP
    digits are used from the USPS response; the original address formatting is
    preserved by the caller.
    """
    if not settings.USPS_USER_ID or not address:
        return None

    street, city, state, zip5 = _parse_for_usps(address)
    if not street or not zip5:
        return None

    xml_req = (
        f'<AddressValidateRequest USERID="{settings.USPS_USER_ID}">'
        "<Revision>1</Revision>"
        '<Address ID="0">'
        "<Address1></Address1>"
        f"<Address2>{street.upper()}</Address2>"
        f"<City>{city.upper()}</City>"
        f"<State>{state.upper()}</State>"
        f"<Zip5>{zip5}</Zip5>"
        "<Zip4></Zip4>"
        "</Address>"
        "</AddressValidateRequest>"
    )

    try:
        resp = await client.get(
            _USPS_URL,
            params={"API": "Verify", "XML": xml_req},
            timeout=5.0,
        )
        if resp.status_code != 200:
            log.warning("USPS ZIP+4 HTTP %s for %r", resp.status_code, address[:60])
            return None

        root = ET.fromstring(resp.text)
        addr_el = root.find("Address")
        if addr_el is None:
            return None

        error_el = addr_el.find("Error")
        if error_el is not None:
            desc = error_el.findtext("Description", "")
            log.info("USPS ZIP+4 no match for %r: %s", address[:60], desc)
            return None

        zip5_val = (addr_el.findtext("Zip5") or "").strip()
        zip4_val = (addr_el.findtext("Zip4") or "").strip()

        if zip5_val and zip4_val and zip4_val not in ("", "0000"):
            result = f"{zip5_val}-{zip4_val}"
            log.info("USPS ZIP+4 %r → %s", address[:60], result)
            return result

        return None
    except Exception as exc:
        log.warning("USPS ZIP+4 error for %r: %s", address[:60], exc)
        return None


def substitute_zip4(address: str, full_zip4: str) -> str:
    """Replace the bare 5-digit ZIP in *address* with *full_zip4* ('NNNNN-NNNN').

    Only replaces the first occurrence that is not already in ZIP+4 form.
    """
    zip5 = full_zip4[:5]
    return re.sub(
        r"\b" + re.escape(zip5) + r"\b(?!-\d{4})",
        full_zip4,
        address,
        count=1,
    )

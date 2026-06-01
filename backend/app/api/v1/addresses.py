"""Address enrichment endpoint — ZIP+4 lookup via Radar + USPS fallback."""

import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends

from app.core.config import settings
from app.dependencies import CurrentUser, get_current_user
from app.services import usps_service

router = APIRouter(tags=["addresses"])
log = logging.getLogger(__name__)


async def _enrich(address: str, client: httpx.AsyncClient) -> str:
    """Return address enriched with ZIP+4.  Tries Radar first; falls back to USPS."""
    if not address:
        return address

    # ── Radar ──────────────────────────────────────────────────────────────────
    if settings.RADAR_API_KEY:
        try:
            resp = await client.get(
                "https://api.radar.io/v1/geocode/forward",
                params={"query": address, "country": "US", "limit": 1},
                headers={"Authorization": settings.RADAR_API_KEY},
                timeout=3.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                addr = (data.get("addresses") or [None])[0]
                if addr:
                    postal = addr.get("postalCode") or ""
                    if "-" in postal:
                        # Radar already has ZIP+4 — build label and return
                        formatted = addr.get("formattedAddress", "")
                        if formatted:
                            log.info("Radar ZIP+4 for %r → %r", address[:60], formatted)
                            return formatted
                        # Build from components
                        parts: list[str] = []
                        street = f"{addr.get('number', '')} {addr.get('street', '')}".strip()
                        if street:
                            parts.append(street)
                        if addr.get("city"):
                            parts.append(addr["city"])
                        state = addr.get("stateCode", "")
                        if state and postal:
                            parts.append(f"{state} {postal}")
                        elif state:
                            parts.append(state)
                        elif postal:
                            parts.append(postal)
                        enriched = ", ".join(parts) if parts else address
                        log.info("Radar ZIP+4 for %r → %r", address[:60], enriched)
                        return enriched
            else:
                log.warning("Radar ZIP+4 HTTP %s for %r", resp.status_code, address[:60])
        except Exception as exc:
            log.warning("Radar ZIP+4 error for %r: %s", address[:60], exc)

    # ── USPS fallback ──────────────────────────────────────────────────────────
    zip4 = await usps_service.lookup_zip4(address, client)
    if zip4:
        return usps_service.substitute_zip4(address, zip4)

    return address


@router.get("/addresses/zip4")
async def get_zip4(
    address: str,
    _current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict:
    """Enrich *address* with a ZIP+4 suffix.

    Tries Radar (secret key, server-side) then USPS as fallback.
    Returns `{"address": "<enriched>"}` — identical to input when no ZIP+4 found.
    """
    async with httpx.AsyncClient(timeout=8) as client:
        enriched = await _enrich(address.strip(), client)
    return {"address": enriched}

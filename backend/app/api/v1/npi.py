import re
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.auth import get_current_user
from app.schemas.auth import CurrentUser

router = APIRouter(tags=["npi"])

NPPES_URL = "https://npiregistry.cms.hhs.gov/api/"


@router.get("/npi/lookup")
async def lookup_npi(
    number: Annotated[str, Query(min_length=10, max_length=10)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict:
    """Proxy the NPPES Read API to avoid browser CORS restrictions."""
    if not re.fullmatch(r"\d{10}", number):
        raise HTTPException(status_code=400, detail="NPI must be exactly 10 digits")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                NPPES_URL,
                params={"version": "2.1", "number": number, "limit": 1},
            )
        data = r.json()
    except Exception:
        raise HTTPException(status_code=502, detail="NPPES registry unreachable")

    results = data.get("results") or []
    if not results:
        raise HTTPException(status_code=404, detail="NPI not found in NPPES registry")

    entry = results[0]
    basic = entry.get("basic") or {}

    if basic.get("organization_name"):
        name = basic["organization_name"]
    else:
        parts = [basic.get("first_name"), basic.get("middle_name"), basic.get("last_name")]
        name = " ".join(p for p in parts if p)
        if basic.get("credential"):
            name += f", {basic['credential']}"

    taxonomies = entry.get("taxonomies") or []
    primary_taxonomy = next(
        (t.get("desc") for t in taxonomies if t.get("primary")),
        taxonomies[0].get("desc") if taxonomies else None,
    )

    return {"name": name, "taxonomy": primary_taxonomy}

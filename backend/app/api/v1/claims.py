import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.audit import AuditLogger
from app.core.config import settings
from app.core.encryption import decrypt_field
from app.dependencies import CurrentUser, get_audit, get_client_ip, get_current_user, get_db, get_user_agent
from app.models.patient import Patient
from app.models.user import User
from app.models.visit import Visit
from app.schemas.claim import ClaimCreate, ClaimRead, ManualClaimUpsert
from app.services import cms1500_service, usps_service
from app.services.claims_service import ClaimsService

router = APIRouter(tags=["claims"])
log = logging.getLogger(__name__)


async def _enrich_zip4(address: str, client: "httpx.AsyncClient") -> str:
    """Return address enriched with ZIP+4.  Tries Radar first, then USPS.

    RADAR_API_KEY must be the Radar *secret* key (prj_live_sk_…).
    The publishable key is domain-restricted and returns 403 from a server.
    """
    if not address:
        return address

    radar_formatted: str | None = None  # Radar-reformatted address (without ZIP+4)

    # ── Try Radar ────────────────────────────────────────────────────────────
    if settings.RADAR_API_KEY:
        try:
            resp = await client.get(
                "https://api.radar.io/v1/geocode/forward",
                params={"query": address, "country": "US", "limit": 1},
                headers={"Authorization": settings.RADAR_API_KEY},
                timeout=3.0,
            )
            if resp.status_code != 200:
                log.warning(
                    "Radar ZIP+4 enrichment HTTP %s for %r — %s. "
                    "Set RADAR_API_KEY to the Radar secret key (prj_live_sk_…), not the publishable key.",
                    resp.status_code, address[:60], resp.text[:200],
                )
            else:
                data = resp.json()
                addr = (data.get("addresses") or [None])[0]
                if addr:
                    formatted = addr.get("formattedAddress", "")
                    if not formatted:
                        parts: list[str] = []
                        street = f"{addr.get('number', '')} {addr.get('street', '')}".strip()
                        if street:
                            parts.append(street)
                        if addr.get("city"):
                            parts.append(addr["city"])
                        state = addr.get("stateCode", "")
                        postal = addr.get("postalCode", "")
                        if state and postal:
                            parts.append(f"{state} {postal}")
                        elif state:
                            parts.append(state)
                        elif postal:
                            parts.append(postal)
                        formatted = ", ".join(parts) if parts else address

                    if "-" in (addr.get("postalCode") or ""):
                        log.info("Radar ZIP+4 enriched %r → %r", address[:60], formatted)
                        return formatted

                    # Radar matched the address but has no ZIP+4
                    radar_formatted = formatted
        except Exception as exc:
            log.warning("Radar ZIP+4 enrichment error for %r: %s", address[:60], exc)

    # ── Try USPS fallback ────────────────────────────────────────────────────
    zip4 = await usps_service.lookup_zip4(address, client)
    if zip4:
        base = radar_formatted if radar_formatted else address
        return usps_service.substitute_zip4(base, zip4)

    # No ZIP+4 found — return Radar-formatted address if we got one, else original
    return radar_formatted if radar_formatted else address


def _svc(db: AsyncSession, audit: AuditLogger) -> ClaimsService:
    return ClaimsService(db, audit)


@router.post("/patients/{patient_id}/claims", response_model=ClaimRead, status_code=status.HTTP_201_CREATED)
async def submit_claim(
    request: Request,
    patient_id: uuid.UUID,
    body: ClaimCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> ClaimRead:
    try:
        return await _svc(db, audit).submit_claim(
            patient_id, current_user.id, body, get_client_ip(request), get_user_agent(request)
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/patients/{patient_id}/claims", response_model=list[ClaimRead])
async def list_claims(
    patient_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> list[ClaimRead]:
    return await _svc(db, audit).list_claims(current_user.id, patient_id)


@router.get("/patients/{patient_id}/visits/{visit_type}/cms1500.pdf")
async def download_cms1500(
    request: Request,
    patient_id: uuid.UUID,
    visit_type: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> Response:
    patient_result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = patient_result.scalar_one_or_none()
    if not patient or not patient.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    user_result = await db.execute(select(User).where(User.id == current_user.id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    visit_result = await db.execute(
        select(Visit).where(Visit.patient_id == patient_id, Visit.visit_type == visit_type)
    )
    visit = visit_result.scalar_one_or_none()

    from datetime import date as date_type
    from app.core.encryption import decrypt_field as _decrypt
    from app.services.ocr_service import get_signed_url
    import httpx as _httpx

    svc_date: date_type | None = None
    if visit and visit.visit_date:
        svc_date = visit.visit_date
    elif visit and visit.visit_started_at:
        svc_date = visit.visit_started_at.date()

    location_type = visit.location_type if visit else None

    async with _httpx.AsyncClient(timeout=10) as hc:
        # Fetch signature image bytes for overlay (non-blocking on failure)
        async def _fetch_bytes(path: str | None) -> bytes | None:
            if not path:
                return None
            try:
                url = await get_signed_url(path, expires_in=60)
                resp = await hc.get(url)
                if resp.status_code == 200:
                    return resp.content
            except Exception:
                pass
            return None

        ma91_sig_bytes = await _fetch_bytes(visit.ma91_signature_path if visit else None)
        provider_sig_bytes = await _fetch_bytes(user.provider_signature_path)

        # Enrich both addresses with ZIP+4 from Radar forward geocode
        patient_address = await _enrich_zip4(patient.address or "", hc)
        provider_address = await _enrich_zip4(user.provider_address or "", hc)

    provider_ssn = ""
    if user.provider_ssn_encrypted:
        try:
            provider_ssn = _decrypt(user.provider_ssn_encrypted)
        except Exception:
            pass

    try:
        pdf_bytes = cms1500_service.generate_pdf(
            patient_data={
                "name": decrypt_field(patient.name_encrypted),
                "medicaid_id": decrypt_field(patient.medicaid_id_encrypted),
                "date_of_birth": patient.date_of_birth,
                "gender": patient.gender,
                "address": patient_address,
                "mco": patient.mco or "",
                "policy_group": patient.policy_group or "",
                "referring_provider_npi": patient.referring_provider_npi or "",
                "referring_provider_name": patient.referring_provider_name or "",
                "has_other_insurance": patient.has_other_insurance,
                "ma91_signed_at": visit.ma91_signed_at if visit else None,
                "ma91_signature_bytes": ma91_sig_bytes,
            },
            visit_data={
                "visit_type": visit_type,
                "visit_date": svc_date,
                "visit_id": str(visit.id).replace("-", "") if visit else "",
                "location_type": location_type,
                "prior_auth_number": visit.prior_auth_number if visit else None,
                "alternate_location": visit.alternate_location if visit else None,
            },
            provider_data={
                "npi": user.npi or "",
                "full_name": user.full_name or "",
                "billing_provider_name": user.billing_provider_name or user.full_name or "",
                "provider_address": provider_address,
                "provider_phone": user.provider_phone or "",
                "provider_ssn": provider_ssn,
                "provider_signature_bytes": provider_sig_bytes,
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    await audit.log(
        action="GENERATE_CMS1500",
        resource_type="patient",
        resource_id=patient_id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        user_id=current_user.id,
        extra_context={"visit_type": visit_type},
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="cms1500_{visit_type}.pdf"'},
    )


@router.put("/patients/{patient_id}/visits/{visit_type}/claims/manual", response_model=ClaimRead)
async def log_manual_claim(
    request: Request,
    patient_id: uuid.UUID,
    visit_type: str,
    body: ManualClaimUpsert,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> ClaimRead:
    try:
        return await _svc(db, audit).log_manual_claim(
            patient_id, current_user.id, visit_type, body,
            get_client_ip(request), get_user_agent(request)
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/claims/{claim_id}/status-check", response_model=ClaimRead)
async def check_claim_status(
    request: Request,
    claim_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditLogger, Depends(get_audit)],
) -> ClaimRead:
    try:
        return await _svc(db, audit).check_claim_status(
            claim_id, current_user.id, get_client_ip(request), get_user_agent(request)
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

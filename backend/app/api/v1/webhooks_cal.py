import hashlib
import hmac
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.lead import Lead

log = logging.getLogger(__name__)

router = APIRouter(prefix="/public/leads", tags=["public"])


async def _find_lead_by_uid(db: AsyncSession, uid: str) -> Lead | None:
    result = await db.execute(select(Lead).where(Lead.cal_booking_uid == uid))
    return result.scalar_one_or_none()


async def _find_lead_by_email(db: AsyncSession, email: str) -> Lead | None:
    result = await db.execute(
        select(Lead).where(Lead.email == email).order_by(Lead.created_at.desc())
    )
    return result.scalar_one_or_none()


def _merge_cal_booking(existing_data: dict | None, booking_payload: dict) -> dict:
    data = dict(existing_data or {})
    data["cal_booking"] = booking_payload
    return data


def _parse_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split(" ", 1)
    return (parts[0], parts[1]) if len(parts) == 2 else (parts[0], "")


async def _notify_admin(lead: Lead) -> None:
    try:
        from app.services.email_service import send_new_lead_notification
        await send_new_lead_notification(lead)
    except Exception:
        log.warning("Failed to send admin lead notification for cal booking", exc_info=True)


@router.post("/cal", status_code=status.HTTP_200_OK)
async def cal_webhook(request: Request) -> dict:
    from app.core.config import settings
    from app.dependencies import _AsyncSession

    body = await request.body()

    if settings.CAL_COM_WEBHOOK_SECRET:
        sig_header = request.headers.get("X-Cal-Signature-256", "")
        computed = "sha256=" + hmac.new(
            settings.CAL_COM_WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(sig_header, computed):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    import json
    try:
        event = json.loads(body)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    trigger = event.get("triggerEvent", "")
    payload = event.get("payload", {})
    booking_uid = payload.get("uid", "")

    log.info("cal_webhook: trigger=%s uid=%s", trigger, booking_uid)

    async with _AsyncSession() as db:
        if trigger == "BOOKING_CREATED":
            attendees = payload.get("attendees", [])
            if not attendees:
                log.warning("cal_webhook: BOOKING_CREATED with no attendees, uid=%s", booking_uid)
                return {"received": True}

            attendee = attendees[0]
            email = str(attendee.get("email", "")).lower()
            if not email:
                return {"received": True}

            start_time_str = payload.get("startTime")
            follow_up_at = None
            if start_time_str:
                try:
                    follow_up_at = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                except ValueError:
                    pass

            existing = await _find_lead_by_email(db, email)

            if existing:
                if existing.converted_user_id:
                    log.info("cal_webhook: lead already converted, email=%s", email)
                    return {"received": True}
                existing.status = "demo_scheduled"
                existing.cal_booking_uid = booking_uid
                existing.lead_data = _merge_cal_booking(existing.lead_data, payload)
                if follow_up_at:
                    existing.follow_up_at = follow_up_at
                existing.updated_at = datetime.now(timezone.utc)
                await db.commit()
                log.info("cal_webhook: updated existing lead email=%s status=demo_scheduled", email)
            else:
                attendee_name = attendee.get("name", "")
                first_name, last_name = _parse_name(attendee_name)
                lead = Lead(
                    source="cal_com",
                    status="demo_scheduled",
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    provider_type="unknown",
                    cal_booking_uid=booking_uid,
                    lead_data={"cal_booking": payload},
                    follow_up_at=follow_up_at,
                )
                db.add(lead)
                await db.commit()
                await db.refresh(lead)
                await _notify_admin(lead)
                log.info("cal_webhook: created new lead email=%s status=demo_scheduled", email)

        elif trigger == "BOOKING_RESCHEDULED":
            lead = await _find_lead_by_uid(db, booking_uid)
            if lead:
                start_time_str = payload.get("startTime")
                if start_time_str:
                    try:
                        lead.follow_up_at = datetime.fromisoformat(
                            start_time_str.replace("Z", "+00:00")
                        )
                    except ValueError:
                        pass
                lead.lead_data = _merge_cal_booking(lead.lead_data, payload)
                lead.updated_at = datetime.now(timezone.utc)
                await db.commit()
                log.info("cal_webhook: rescheduled lead uid=%s", booking_uid)

        elif trigger == "BOOKING_CANCELLED":
            lead = await _find_lead_by_uid(db, booking_uid)
            if lead:
                if lead.status == "demo_scheduled":
                    lead.status = "qualified"
                lead.follow_up_at = None
                lead.lead_data = _merge_cal_booking(lead.lead_data, payload)
                lead.updated_at = datetime.now(timezone.utc)
                await db.commit()
                log.info("cal_webhook: cancelled lead uid=%s reverted to qualified", booking_uid)

        elif trigger == "RECORDING_READY":
            lead = await _find_lead_by_uid(db, booking_uid)
            if lead:
                data = dict(lead.lead_data or {})
                data["cal_recording"] = payload
                lead.lead_data = data
                lead.updated_at = datetime.now(timezone.utc)
                await db.commit()
                log.info("cal_webhook: recording stored for lead uid=%s", booking_uid)
            else:
                log.warning("cal_webhook: RECORDING_READY — no lead found for uid=%s", booking_uid)

        elif trigger == "TRANSCRIPT_READY":
            lead = await _find_lead_by_uid(db, booking_uid)
            if lead:
                data = dict(lead.lead_data or {})
                data["cal_transcript"] = payload
                lead.lead_data = data
                lead.updated_at = datetime.now(timezone.utc)
                await db.commit()
                log.info("cal_webhook: transcript stored for lead uid=%s", booking_uid)
            else:
                log.warning("cal_webhook: TRANSCRIPT_READY — no lead found for uid=%s", booking_uid)

    return {"received": True}

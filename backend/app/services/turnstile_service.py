import logging

import httpx
from fastapi import HTTPException, Request, status

from app.core.config import settings

log = logging.getLogger(__name__)

_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile_or_raise(token: str | None, request: Request) -> None:
    """Verify a Cloudflare Turnstile token from the public landing page.

    Fail-open when TURNSTILE_SECRET_KEY isn't configured yet, so this can ship and
    deploy before the Railway env var is set without blocking any leads — once the
    secret key is set, verification is enforced and this fails closed (missing or
    invalid token => 403). Also fails open (logs + allows) if Cloudflare's own API
    is unreachable, so a Cloudflare outage doesn't take down lead capture.
    """
    if not settings.TURNSTILE_SECRET_KEY:
        return

    if not token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing bot-verification token.")

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                _VERIFY_URL,
                data={
                    "secret": settings.TURNSTILE_SECRET_KEY,
                    "response": token,
                    "remoteip": request.client.host if request.client else "",
                },
            )
        if resp.status_code != 200:
            log.warning("Turnstile siteverify HTTP %s: %s", resp.status_code, resp.text[:200])
            return  # fail open on Cloudflare-side errors, not a token problem

        result = resp.json()
        if not result.get("success"):
            log.info("Turnstile verification failed: %s", result.get("error-codes"))
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bot verification failed.")
    except HTTPException:
        raise
    except Exception as exc:
        log.warning("Turnstile verification request error: %s", exc)
        # Network/Cloudflare-outage failure, not a bad token — fail open.

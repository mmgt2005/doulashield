"""Public webinar AI Q&A chat endpoint.

The marketing landing page sends visitor questions here; this handler
proxies them to Anthropic's Messages API server-side so the API key is
never exposed to the browser.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.schemas.webinar_chat import WebinarChatRequest

log = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/public", tags=["public"])

_MAX_TURNS = 20
_MAX_TOKENS = 400
_MODEL = "claude-haiku-4-5-20251001"


@router.post("/webinar-chat", response_model=None)
@limiter.limit("10/minute")
async def webinar_chat(request: Request, body: WebinarChatRequest) -> dict:
    """Proxy a webinar Q&A chat turn to the Anthropic Messages API."""
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat unavailable",
        )

    try:
        import anthropic

        messages = [
            {"role": m.role, "content": m.content}
            for m in body.messages[-_MAX_TURNS:]
        ]

        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = await client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=body.system,
            messages=messages,
        )

        reply = response.content[0].text if response.content else ""
        return {"reply": reply}

    except Exception:
        log.exception("webinar_chat: Anthropic call failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat unavailable",
        )

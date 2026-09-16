from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class WebinarChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class WebinarChatRequest(BaseModel):
    system: str
    messages: list[WebinarChatMessage] = Field(..., min_length=1)

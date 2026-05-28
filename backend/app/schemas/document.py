from __future__ import annotations

from pydantic import BaseModel


class DocumentSubmitResponse(BaseModel):
    availity_document_id: str
    status: str

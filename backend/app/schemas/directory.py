from __future__ import annotations

from pydantic import BaseModel


class DirectoryProvider(BaseModel):
    npi: str | None
    name: str | None
    specialty: str | None
    address: str | None
    phone: str | None


class DirectorySearchResponse(BaseModel):
    providers: list[DirectoryProvider]
    total: int

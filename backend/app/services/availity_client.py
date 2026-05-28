from __future__ import annotations

import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

AVAILITY_BASE = "https://api.availity.com/availity/v1"
AVAILITY_TOKEN_URL = f"{AVAILITY_BASE}/token"

MCO_PAYER_IDS: dict[str, str] = {
    "AmeriHealth Caritas": "AMCRN",
    "UPMC For You": "UPMCF",
    "Geisinger Health Plan": "GEISP",
    "Health Partners Plans": "HLTHP",
    "Aetna Better Health": "AETNB",
    "UnitedHealthcare Community Plan": "87726",
    "Highmark Wholecare": "HMKWC",
    "FFS": "77799",
}

# Module-level token cache: { user_id: (token, expires_at_epoch) }
_token_cache: dict[str, tuple[str, float]] = {}


class AvailityClient:
    """Reusable async Availity API client with per-provider OAuth token caching."""

    def __init__(self, client_id: str, client_secret: str, user_id: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._user_id = user_id

    async def get_token(self) -> str:
        cached = _token_cache.get(self._user_id)
        if cached and time.time() < cached[1]:
            return cached[0]

        async with httpx.AsyncClient(timeout=15) as http:
            resp = await http.post(
                AVAILITY_TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        token = data["access_token"]
        expires_in = int(data.get("expires_in", 3600))
        _token_cache[self._user_id] = (token, time.time() + expires_in - 60)
        return token

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        token = await self.get_token()
        async with httpx.AsyncClient(timeout=20) as http:
            resp = await http.get(
                f"{AVAILITY_BASE}{path}",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            return resp.json()

    async def post(self, path: str, body: dict) -> dict:
        token = await self.get_token()
        async with httpx.AsyncClient(timeout=20) as http:
            resp = await http.post(
                f"{AVAILITY_BASE}{path}",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            return resp.json()

    async def post_multipart(self, path: str, files: dict, data: dict) -> dict:
        token = await self.get_token()
        async with httpx.AsyncClient(timeout=30) as http:
            resp = await http.post(
                f"{AVAILITY_BASE}{path}",
                files=files,
                data=data,
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            return resp.json()

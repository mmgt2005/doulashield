"""UHC (UnitedHealthcare Community Plan) direct API client.

Uses OAuth2 with PKCE (S256 code challenge). Token is cached in-process
with a 55-minute TTL (UHC tokens typically expire in 60 minutes).

Base URL and exact endpoint paths should be verified against UHC developer
documentation at uhcprovider.com/api before going live.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

UHC_BASE = "https://api.uhc.com/ClaimsApi/v1"
UHC_TOKEN_URL = "https://api.uhc.com/oauth2/token"

# Module-level token cache: { user_id: (token, expires_at_epoch) }
_token_cache: dict[str, tuple[str, float]] = {}


def _pkce_pair() -> tuple[str, str]:
    """Generate a PKCE code_verifier + code_challenge (S256)."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


class UHCClient:
    """Async UHC Claims API client with per-provider PKCE OAuth2 token caching."""

    def __init__(self, client_id: str, client_secret: str, user_id: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._user_id = user_id

    async def get_token(self) -> str:
        cached = _token_cache.get(self._user_id)
        if cached and time.time() < cached[1]:
            return cached[0]

        verifier, challenge = _pkce_pair()

        async with httpx.AsyncClient(timeout=15) as http:
            resp = await http.post(
                UHC_TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "code_challenge": challenge,
                    "code_challenge_method": "S256",
                    "code_verifier": verifier,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        token = data["access_token"]
        expires_in = int(data.get("expires_in", 3600))
        # Cache with 55-minute TTL regardless of server-reported expiry
        ttl = min(expires_in - 60, 55 * 60)
        _token_cache[self._user_id] = (token, time.time() + ttl)
        return token

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        token = await self.get_token()
        async with httpx.AsyncClient(timeout=20) as http:
            resp = await http.get(
                f"{UHC_BASE}{path}",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            return resp.json()

    async def post(self, path: str, body: dict) -> dict:
        token = await self.get_token()
        async with httpx.AsyncClient(timeout=20) as http:
            resp = await http.post(
                f"{UHC_BASE}{path}",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            return resp.json()

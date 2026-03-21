"""OAuth2 token management for the Airtel Open API."""

from __future__ import annotations

import time

import requests

from .exceptions import AuthenticationError


class TokenManager:
    """
    Manages an OAuth2 access token for the Airtel Open API.

    Automatically re-fetches the token when it expires so callers never
    have to think about token lifecycle.

    Parameters
    ----------
    client_id:
        Your Airtel application's Client ID (from Key Management).
    client_secret:
        Your Airtel application's Client Secret (from Key Management).
    base_url:
        The Airtel API base URL (sandbox or production).
    """

    _TOKEN_PATH = "/auth/oauth2/token"

    def __init__(self, client_id: str, client_secret: str, base_url: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._base_url = base_url.rstrip("/")

        self._access_token: str | None = None
        self._expires_at: float = 0.0  # unix timestamp

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def access_token(self) -> str:
        """Return a valid access token, refreshing it if necessary."""
        if self._is_expired():
            self._fetch_token()
        return self._access_token  # type: ignore[return-value]

    def invalidate(self) -> None:
        """Force the next call to ``access_token`` to re-authenticate."""
        self._expires_at = 0.0
        self._access_token = None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _is_expired(self) -> bool:
        # Refresh 60 seconds before actual expiry to avoid edge-case failures
        return time.time() >= (self._expires_at - 60)

    def _fetch_token(self) -> None:
        url = f"{self._base_url}{self._TOKEN_PATH}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
        }
        payload = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "grant_type": "client_credentials",
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
        except requests.RequestException as exc:
            raise AuthenticationError(f"Network error while fetching token: {exc}") from exc

        if response.status_code != 200:
            raise AuthenticationError(
                f"Token request failed [{response.status_code}]: {response.text}"
            )

        data = response.json()

        token = data.get("access_token")
        if not token:
            raise AuthenticationError(f"No access_token in response: {data}")

        expires_in = int(data.get("expires_in", 3600))
        self._access_token = token
        self._expires_at = time.time() + expires_in

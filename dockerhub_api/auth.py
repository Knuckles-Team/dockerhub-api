"""Docker Hub authentication.

CONCEPT:HUB-1.1 — JWT auth lifecycle.

Docker Hub's v2 API authenticates with a short-lived JWT minted from
``POST /v2/auth/token`` using an *identifier* (username or organization name)
and a *secret* (account password, personal access token ``dckr_pat_*``, or an
organization access token). This module owns that lifecycle:

- :class:`TokenManager` — mints the JWT, caches it, and refreshes it before
  expiry (``exp`` claim parsed straight from the JWT payload, no signature
  verification needed client-side).
- :func:`get_client` — factory that builds the :class:`~dockerhub_api.api_client.Api`
  client from explicit arguments or ``DOCKERHUB_*`` environment variables.

Secrets are never logged; only derived metadata (expiry, identifier) is.
"""

import base64
import binascii
import json
import os
import threading
import time
from typing import Any

import httpx
from agent_utilities.base_utilities import get_logger, to_boolean
from agent_utilities.core.exceptions import AuthError

logger = get_logger(__name__)

DEFAULT_DOCKERHUB_URL = "https://hub.docker.com"
AUTH_ENDPOINT = "/v2/auth/token"
#: Fallback token lifetime (seconds) when the JWT carries no readable ``exp``.
DEFAULT_TOKEN_TTL = 300.0
#: Refresh this many seconds *before* the JWT actually expires.
DEFAULT_REFRESH_SKEW = 60.0

_token_manager_lock = threading.Lock()
_token_managers: dict[tuple, "TokenManager"] = {}


def decode_jwt_claims(token: str) -> dict[str, Any]:
    """Best-effort decode of a JWT payload segment (no signature verification).

    Returns an empty dict when the token is not a parseable JWT.
    """
    try:
        segments = token.split(".")
        if len(segments) < 2:
            return {}
        payload = segments[1]
        payload += "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload.encode("utf-8"))
        claims = json.loads(decoded)
        return claims if isinstance(claims, dict) else {}
    except (ValueError, binascii.Error, UnicodeDecodeError):
        return {}


class TokenManager:
    """Caches the Docker Hub JWT and refreshes it before expiry.

    Thread-safe: concurrent callers share a single cached token and only one
    mint request is in flight at a time.
    """

    def __init__(
        self,
        identifier: str,
        secret: str,
        url: str = DEFAULT_DOCKERHUB_URL,
        verify: bool = True,
        timeout: float = 30.0,
        refresh_skew: float = DEFAULT_REFRESH_SKEW,
        transport: httpx.BaseTransport | None = None,
    ):
        if not identifier or not secret:
            raise AuthError("Docker Hub identifier and secret are both required.")
        self.identifier = identifier
        self._secret = secret
        self.url = url.rstrip("/")
        self.verify = verify
        self.timeout = timeout
        self.refresh_skew = refresh_skew
        self._transport = transport
        self._lock = threading.Lock()
        self._token: str | None = None
        self._claims: dict[str, Any] = {}
        self._expires_at: float = 0.0

    def get_token(self) -> str:
        """Return a valid JWT, minting a fresh one when (nearly) expired."""
        with self._lock:
            if self._token and time.time() < (self._expires_at - self.refresh_skew):
                return self._token
            return self._fetch()

    def claims(self) -> dict[str, Any]:
        """Return the decoded claims of the current JWT (minting if needed)."""
        self.get_token()
        return dict(self._claims)

    def invalidate(self) -> None:
        """Drop the cached token so the next call mints a fresh one."""
        with self._lock:
            self._token = None
            self._claims = {}
            self._expires_at = 0.0

    @property
    def expires_at(self) -> float:
        return self._expires_at

    def _fetch(self) -> str:
        response = httpx.Client(
            base_url=self.url,
            verify=self.verify,
            timeout=self.timeout,
            transport=self._transport,
        ).post(
            AUTH_ENDPOINT,
            json={"identifier": self.identifier, "secret": self._secret},
        )
        if response.status_code in (401, 403):
            raise AuthError(
                f"Docker Hub rejected the credentials for '{self.identifier}' "
                f"(HTTP {response.status_code})."
            )
        if response.status_code >= 400:
            raise AuthError(
                f"Docker Hub token mint failed with HTTP {response.status_code}."
            )
        body = response.json()
        token = body.get("access_token") or body.get("token")
        if not token:
            raise AuthError("Docker Hub token response did not include a token.")
        self._token = token
        self._claims = decode_jwt_claims(token)
        exp = self._claims.get("exp")
        if isinstance(exp, (int, float)) and exp > 0:
            self._expires_at = float(exp)
        else:
            self._expires_at = time.time() + DEFAULT_TOKEN_TTL
        logger.info(
            "Minted Docker Hub JWT",
            extra={
                "identifier": self.identifier,
                "expires_at": self._expires_at,
            },
        )
        return self._token


def get_token_manager(
    identifier: str,
    secret: str,
    url: str = DEFAULT_DOCKERHUB_URL,
    verify: bool = True,
) -> TokenManager:
    """Return a shared, process-wide :class:`TokenManager` for the credentials.

    Sharing the manager lets every short-lived client (one per MCP tool call)
    reuse the same cached JWT instead of re-minting on every request.
    """
    key = (url.rstrip("/"), identifier, verify)
    with _token_manager_lock:
        manager = _token_managers.get(key)
        if manager is None or manager._secret != secret:
            manager = TokenManager(
                identifier=identifier, secret=secret, url=url, verify=verify
            )
            _token_managers[key] = manager
        return manager


def get_client(
    url: str | None = None,
    username: str | None = None,
    token: str | None = None,
    jwt: str | None = None,
    verify: bool | None = None,
    allow_destructive: bool | None = None,
    config: dict | None = None,
) -> Any:
    """Factory for the Docker Hub :class:`~dockerhub_api.api_client.Api` client.

    Credential resolution order:

    1. ``jwt`` / ``DOCKERHUB_JWT`` — a pre-minted bearer used as-is.
    2. ``username`` + ``token`` — from the OFFICIAL hub-tool environment names
       ``DOCKER_HUB_USER`` + ``DOCKER_HUB_TOKEN`` (primary), falling back to
       ``DOCKERHUB_USERNAME`` + ``DOCKERHUB_TOKEN`` — exchanged for a
       short-lived JWT via a shared :class:`TokenManager` (the secret may be a
       password, a PAT ``dckr_pat_*``, or an org token).
    3. Anonymous — public, unauthenticated endpoints only.

    ``DOCKERHUB_ALLOW_DESTRUCTIVE`` (default ``False``) gates deletes and
    org-settings writes. CONCEPT:HUB-1.3 — destructive-action gating.
    """
    from dockerhub_api.api_client import Api

    config = config or {}
    url = str(
        url or config.get("url") or os.getenv("DOCKERHUB_URL") or DEFAULT_DOCKERHUB_URL
    )
    username = (
        username
        or config.get("username")
        or os.getenv("DOCKER_HUB_USER")
        or os.getenv("DOCKERHUB_USERNAME")
    )
    token = (
        token
        or config.get("token")
        or os.getenv("DOCKER_HUB_TOKEN")
        or os.getenv("DOCKERHUB_TOKEN")
    )
    jwt = jwt or config.get("jwt") or os.getenv("DOCKERHUB_JWT")
    if verify is None:
        verify = to_boolean(string=os.getenv("DOCKERHUB_SSL_VERIFY", "True"))
    if allow_destructive is None:
        allow_destructive = to_boolean(
            string=os.getenv("DOCKERHUB_ALLOW_DESTRUCTIVE", "False")
        )

    if jwt:
        logger.info("Using pre-minted Docker Hub JWT")
        return Api(
            url=url, token=jwt, verify=verify, allow_destructive=allow_destructive
        )

    if username and token:
        logger.info(
            "Using Docker Hub credential exchange", extra={"identifier": username}
        )
        manager = get_token_manager(
            identifier=username, secret=token, url=url, verify=verify
        )
        return Api(
            url=url,
            token_manager=manager,
            verify=verify,
            allow_destructive=allow_destructive,
        )

    logger.warning(
        "No Docker Hub credentials configured — anonymous client "
        "(public endpoints only). Set DOCKERHUB_USERNAME and DOCKERHUB_TOKEN."
    )
    return Api(url=url, verify=verify, allow_destructive=allow_destructive)

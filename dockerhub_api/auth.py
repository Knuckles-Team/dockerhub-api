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

#: Registry HTTP API v2 host (manifests, blobs, tags — a *different* API and
#: auth model than the ``hub.docker.com`` management API above).
DEFAULT_REGISTRY_URL = "https://registry-1.docker.io"
#: Token-service realm and service used to mint per-repository registry
#: bearers. These are the Docker Hub defaults; the values actually used are
#: preferred from each ``WWW-Authenticate`` challenge so mirrors work too.
DEFAULT_REGISTRY_AUTH_REALM = "https://auth.docker.io/token"
DEFAULT_REGISTRY_SERVICE = "registry.docker.io"
#: Docker Scout API host (CVE / SBOM / policy data). Authenticated with the
#: same Hub JWT minted from ``/v2/auth/token``.
DEFAULT_SCOUT_URL = "https://api.scout.docker.com"

_token_manager_lock = threading.Lock()
_token_managers: dict[tuple, "TokenManager"] = {}


def parse_www_authenticate(header: str) -> dict[str, str]:
    """Parse a ``WWW-Authenticate: Bearer realm="...",service="..."`` header.

    Returns the ``realm`` / ``service`` / ``scope`` (and any other) directives
    as a flat dict. Returns an empty dict when the header is absent or not a
    Bearer challenge.
    """
    if not header:
        return {}
    scheme, _, rest = header.strip().partition(" ")
    if scheme.lower() != "bearer" or not rest:
        return {}
    directives: dict[str, str] = {}
    for part in rest.split(","):
        key, sep, value = part.strip().partition("=")
        if sep:
            directives[key.strip()] = value.strip().strip('"')
    return directives


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


class RegistryTokenManager:
    """Mints and caches **per-scope** Registry v2 bearer tokens.

    CONCEPT:HUB-1.7 — Registry v2 scoped-token auth. Unlike the single Hub JWT,
    each registry token is scoped to one repository and action set
    (``repository:library/nginx:pull``). Tokens are obtained from a token
    service (default ``auth.docker.io``) with optional HTTP Basic credentials;
    anonymous tokens are issued for public ``pull`` scopes. Thread-safe: one
    cached token per scope, refreshed before expiry.
    """

    def __init__(
        self,
        username: str | None = None,
        secret: str | None = None,
        realm: str = DEFAULT_REGISTRY_AUTH_REALM,
        service: str = DEFAULT_REGISTRY_SERVICE,
        verify: bool = True,
        timeout: float = 30.0,
        refresh_skew: float = DEFAULT_REFRESH_SKEW,
        transport: httpx.BaseTransport | None = None,
    ):
        self.username = username
        self._secret = secret
        self.realm = realm
        self.service = service
        self.verify = verify
        self.timeout = timeout
        self.refresh_skew = refresh_skew
        self._transport = transport
        self._lock = threading.Lock()
        #: scope -> (token, expires_at)
        self._tokens: dict[str, tuple[str, float]] = {}

    def get_token(
        self, scope: str, realm: str | None = None, service: str | None = None
    ) -> str | None:
        """Return a valid bearer for ``scope``, minting one when needed."""
        with self._lock:
            cached = self._tokens.get(scope)
            if cached and time.time() < (cached[1] - self.refresh_skew):
                return cached[0]
            return self._fetch(scope, realm or self.realm, service or self.service)

    def invalidate(self, scope: str) -> None:
        """Drop a cached scope token (used on a 401 re-challenge)."""
        with self._lock:
            self._tokens.pop(scope, None)

    def _fetch(self, scope: str, realm: str, service: str) -> str | None:
        params = {"service": service}
        if scope:
            params["scope"] = scope
        auth = (self.username, self._secret) if self.username and self._secret else None
        response = httpx.Client(
            verify=self.verify,
            timeout=self.timeout,
            transport=self._transport,
        ).get(realm, params=params, auth=auth)
        if response.status_code in (401, 403):
            raise AuthError(
                f"Registry token service rejected scope '{scope}' "
                f"(HTTP {response.status_code})."
            )
        if response.status_code >= 400:
            raise AuthError(
                f"Registry token mint failed with HTTP {response.status_code}."
            )
        body = response.json()
        token = body.get("token") or body.get("access_token")
        if not token:
            return None
        expires_in = body.get("expires_in")
        ttl = float(expires_in) if isinstance(expires_in, (int, float)) else 60.0
        self._tokens[scope] = (token, time.time() + ttl)
        return token


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


def _resolve_credentials(
    username: str | None,
    token: str | None,
    config: dict | None,
) -> tuple[str | None, str | None]:
    """Resolve Hub username/secret from args, config, or environment.

    Shared by the Registry and Scout factories so all three surfaces honour the
    same ``DOCKER_HUB_USER`` / ``DOCKER_HUB_TOKEN`` (and fallback) variables.
    """
    config = config or {}
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
    return username, token


def get_registry_client(
    url: str | None = None,
    username: str | None = None,
    token: str | None = None,
    verify: bool | None = None,
    allow_destructive: bool | None = None,
    config: dict | None = None,
    transport: Any | None = None,
) -> Any:
    """Factory for the :class:`~dockerhub_api.api.api_client_registry.RegistryApi`.

    CONCEPT:HUB-1.7 — Registry v2 client. Authenticates with per-repository
    scoped tokens via :class:`RegistryTokenManager` using the same
    ``DOCKER_HUB_USER`` / ``DOCKER_HUB_TOKEN`` credentials (anonymous when
    unset, which still works for public pulls). Pushes, deletes, and blob
    uploads are gated by ``DOCKERHUB_ALLOW_DESTRUCTIVE``.
    """
    from dockerhub_api.api.api_client_registry import RegistryApi

    config = config or {}
    url = str(
        url
        or config.get("registry_url")
        or os.getenv("DOCKER_REGISTRY_URL")
        or DEFAULT_REGISTRY_URL
    )
    realm = str(
        config.get("registry_auth_realm")
        or os.getenv("DOCKER_REGISTRY_AUTH_URL")
        or DEFAULT_REGISTRY_AUTH_REALM
    )
    username, token = _resolve_credentials(username, token, config)
    if verify is None:
        verify = to_boolean(string=os.getenv("DOCKERHUB_SSL_VERIFY", "True"))
    if allow_destructive is None:
        allow_destructive = to_boolean(
            string=os.getenv("DOCKERHUB_ALLOW_DESTRUCTIVE", "False")
        )

    token_manager = RegistryTokenManager(
        username=username,
        secret=token,
        realm=realm,
        verify=verify,
        transport=transport,
    )
    if username:
        logger.info(
            "Using Docker Registry scoped tokens", extra={"identifier": username}
        )
    else:
        logger.info("Using anonymous Docker Registry tokens (public pulls only)")
    return RegistryApi(
        url=url,
        registry_token_manager=token_manager,
        verify=verify,
        allow_destructive=allow_destructive,
        transport=transport,
    )


def get_scout_client(
    url: str | None = None,
    username: str | None = None,
    token: str | None = None,
    jwt: str | None = None,
    verify: bool | None = None,
    config: dict | None = None,
    transport: Any | None = None,
) -> Any:
    """Factory for the :class:`~dockerhub_api.api.api_client_scout.ScoutApi`.

    CONCEPT:HUB-1.11 — Docker Scout client. Reuses the Hub JWT (same
    ``/v2/auth/token`` exchange) but targets ``api.scout.docker.com`` for CVE,
    SBOM, and policy data.
    """
    from dockerhub_api.api.api_client_scout import ScoutApi

    config = config or {}
    url = str(
        url
        or config.get("scout_url")
        or os.getenv("DOCKER_SCOUT_URL")
        or DEFAULT_SCOUT_URL
    )
    hub_url = str(
        config.get("url") or os.getenv("DOCKERHUB_URL") or DEFAULT_DOCKERHUB_URL
    )
    jwt = jwt or config.get("jwt") or os.getenv("DOCKERHUB_JWT")
    username, token = _resolve_credentials(username, token, config)
    if verify is None:
        verify = to_boolean(string=os.getenv("DOCKERHUB_SSL_VERIFY", "True"))

    if jwt:
        return ScoutApi(url=url, token=jwt, verify=verify, transport=transport)
    if username and token:
        manager = get_token_manager(
            identifier=username, secret=token, url=hub_url, verify=verify
        )
        return ScoutApi(
            url=url, token_manager=manager, verify=verify, transport=transport
        )
    logger.warning(
        "No Docker Hub credentials configured — Scout client is anonymous and "
        "most Scout endpoints will be unauthorized."
    )
    return ScoutApi(url=url, verify=verify, transport=transport)

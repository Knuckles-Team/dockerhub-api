"""Base HTTP plumbing for the Docker Hub API client.

CONCEPT:DH-OS.audit.core-wrapper-api-is — core wrapper. Raw ``httpx`` client against
``https://hub.docker.com`` with a uniform response envelope.

CONCEPT:DH-OS.governance.rate-limit-telemetry-every — rate-limit telemetry. Every response's
``X-RateLimit-Limit`` / ``X-RateLimit-Remaining`` / ``X-RateLimit-Reset``
headers are captured into the result envelope (and kept on the client as
``rate_limit``), and HTTP 429 responses are retried with a bounded
``Retry-After`` backoff.

CONCEPT:DH-OS.identity.destructive-action-gating-member — destructive-action gating. Deletes and org-settings writes
raise :class:`DestructiveOperationError` unless the client was built with
``allow_destructive=True``.
"""

import logging
import time
from typing import Any

import httpx
from agent_utilities.base_utilities import get_logger
from agent_utilities.core.exceptions import (
    ApiError,
    AuthError,
    ParameterError,
    UnauthorizedError,
)

logger = get_logger(__name__)

JSON_CONTENT_TYPE = "application/json"
SCIM_CONTENT_TYPE = "application/scim+json"

#: Hard ceiling (seconds) on a single Retry-After sleep so a hostile or
#: misconfigured server can never stall a caller indefinitely.
DEFAULT_RETRY_AFTER_CAP = 15.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30.0


class DestructiveOperationError(PermissionError):
    """Raised when a destructive operation is attempted while gated off."""


class DockerHubApiBase:
    """Shared transport, auth header, retry, and envelope logic."""

    def __init__(
        self,
        url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        token_manager: Any | None = None,
        verify: bool = True,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_after_cap: float = DEFAULT_RETRY_AFTER_CAP,
        allow_destructive: bool = False,
        debug: bool = False,
        transport: httpx.BaseTransport | None = None,
    ):
        if debug:
            logger.setLevel(logging.DEBUG)
            logger.debug("Debug mode enabled")
        else:
            logger.setLevel(logging.ERROR)

        from dockerhub_api.auth import DEFAULT_DOCKERHUB_URL, TokenManager

        self.url = (url or DEFAULT_DOCKERHUB_URL).rstrip("/")
        self.verify = verify
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_after_cap = retry_after_cap
        self.allow_destructive = allow_destructive
        self.debug = debug
        #: Last rate-limit snapshot seen on any response.
        self.rate_limit: dict[str, Any] = {}

        self._static_token: str | None = None
        self._token_manager = None
        if token_manager is not None:
            self._token_manager = token_manager
        elif token:
            self._static_token = token
        elif username and password:
            self._token_manager = TokenManager(
                identifier=username,
                secret=password,
                url=self.url,
                verify=verify,
                timeout=timeout,
                transport=transport,
            )

        self._client = httpx.Client(
            base_url=self.url,
            verify=verify,
            timeout=timeout,
            transport=transport,
        )

    # ------------------------------------------------------------------ #
    # Auth & headers
    # ------------------------------------------------------------------ #

    def _bearer_token(self) -> str | None:
        if self._token_manager is not None:
            return self._token_manager.get_token()
        return self._static_token

    def _build_headers(
        self, content_type: str | None = None, accept: str | None = None
    ) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": accept or JSON_CONTENT_TYPE,
            "Content-Type": content_type or JSON_CONTENT_TYPE,
        }
        token = self._bearer_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    # ------------------------------------------------------------------ #
    # Rate-limit telemetry
    # ------------------------------------------------------------------ #

    def _capture_rate_limit(self, response: httpx.Response) -> dict[str, Any]:
        snapshot: dict[str, Any] = {}
        for header, key in (
            ("X-RateLimit-Limit", "limit"),
            ("X-RateLimit-Remaining", "remaining"),
            ("X-RateLimit-Reset", "reset"),
        ):
            value = response.headers.get(header)
            if value is not None:
                try:
                    snapshot[key] = int(value)
                except ValueError:
                    snapshot[key] = value
        if snapshot:
            self.rate_limit = snapshot
        return snapshot

    def get_rate_limit(self) -> dict[str, Any]:
        """Return the most recent rate-limit snapshot observed by this client."""
        return {
            "status_code": 200,
            "data": dict(self.rate_limit) if self.rate_limit else {},
            "rate_limit": dict(self.rate_limit) if self.rate_limit else {},
        }

    def whoami(self) -> dict[str, Any]:
        """Introspect the active credential locally (decoded JWT claims).

        No network call is made: the cached JWT payload is decoded. For a
        static token the claims are decoded from the supplied bearer.
        """
        from dockerhub_api.auth import decode_jwt_claims

        if self._token_manager is not None:
            claims = self._token_manager.claims()
            identity = getattr(self._token_manager, "identifier", None)
        elif self._static_token:
            claims = decode_jwt_claims(self._static_token)
            identity = claims.get("username") or claims.get("sub")
        else:
            return {
                "status_code": 200,
                "data": {"authenticated": False, "identity": None, "claims": {}},
                "rate_limit": dict(self.rate_limit) if self.rate_limit else {},
            }
        public_claims = {
            key: value
            for key, value in claims.items()
            if key in ("sub", "username", "exp", "iat", "iss", "aud", "scope", "uuid")
        }
        return {
            "status_code": 200,
            "data": {
                "authenticated": True,
                "identity": identity or public_claims.get("username"),
                "claims": public_claims,
            },
            "rate_limit": dict(self.rate_limit) if self.rate_limit else {},
        }

    # ------------------------------------------------------------------ #
    # Destructive gating
    # ------------------------------------------------------------------ #

    def _guard_destructive(self, operation: str) -> None:
        if not self.allow_destructive:
            raise DestructiveOperationError(
                f"Destructive operation '{operation}' is disabled. "
                "Build the client with allow_destructive=True or set "
                "DOCKERHUB_ALLOW_DESTRUCTIVE=True to enable it."
            )

    # ------------------------------------------------------------------ #
    # Request engine
    # ------------------------------------------------------------------ #

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        json: Any | None = None,
        content_type: str | None = None,
        accept: str | None = None,
        raise_for_status: bool = True,
    ) -> dict[str, Any]:
        """Send one API request and return the uniform response envelope.

        Envelope: ``{"status_code": int, "data": Any, "rate_limit": dict}``.
        Handles 429 with bounded Retry-After backoff and one transparent
        token refresh on 401 when a token manager is present.
        """
        if params:
            params = {k: v for k, v in params.items() if v is not None}

        attempts = 0
        refreshed_token = False
        while True:
            response = self._client.request(
                method=method,
                url=endpoint,
                params=params or None,
                json=json,
                headers=self._build_headers(content_type=content_type, accept=accept),
            )
            rate_limit = self._capture_rate_limit(response)

            if response.status_code == 429 and attempts < self.max_retries:
                attempts += 1
                delay = self._retry_after_seconds(response)
                logger.debug(
                    "Rate limited; retrying",
                    extra={"attempt": attempts, "delay": delay},
                )
                if delay > 0:
                    time.sleep(delay)
                continue

            if (
                response.status_code == 401
                and self._token_manager is not None
                and not refreshed_token
            ):
                refreshed_token = True
                self._token_manager.invalidate()
                continue

            break

        data = self._parse_body(response)
        if raise_for_status and response.status_code >= 400:
            self._raise_for_status(response, data)

        return {
            "status_code": response.status_code,
            "data": data,
            "rate_limit": rate_limit or dict(self.rate_limit),
        }

    def _retry_after_seconds(self, response: httpx.Response) -> float:
        raw = response.headers.get("Retry-After", "1")
        try:
            delay = float(raw)
        except ValueError:
            delay = 1.0
        return max(0.0, min(delay, self.retry_after_cap))

    @staticmethod
    def _parse_body(response: httpx.Response) -> Any:
        if response.status_code == 204 or not response.content:
            return None
        content_type = response.headers.get("Content-Type", "")
        if "json" in content_type:
            try:
                return response.json()
            except ValueError:
                return response.text
        return response.text

    def _raise_for_status(self, response: httpx.Response, data: Any) -> None:
        detail = ""
        if isinstance(data, dict):
            detail = str(
                data.get("detail") or data.get("message") or data.get("errinfo") or ""
            )
        message = f"HTTP {response.status_code} for {response.request.method} {response.request.url.path}"
        if detail:
            message = f"{message}: {detail}"

        if response.status_code == 400:
            raise ParameterError(message)
        if response.status_code == 401:
            raise AuthError(message)
        if response.status_code == 403:
            raise UnauthorizedError(message)
        if response.status_code == 404:
            raise ParameterError(message)
        if response.status_code == 429:
            raise ApiError(
                f"{message} — rate limited after {self.max_retries} retries "
                f"(remaining={self.rate_limit.get('remaining')}, "
                f"reset={self.rate_limit.get('reset')})"
            )
        raise ApiError(message)

    def _exists(self, endpoint: str, params: dict | None = None) -> dict[str, Any]:
        """HEAD helper: existence check without raising on 404."""
        envelope = self._request(
            "HEAD", endpoint, params=params, raise_for_status=False
        )
        status_code = envelope["status_code"]
        if status_code not in (200, 404) and status_code >= 400:
            # Map real errors (401/403/5xx); 404 simply means "does not exist".
            if status_code == 401:
                raise AuthError(f"HTTP {status_code} for HEAD {endpoint}")
            if status_code == 403:
                raise UnauthorizedError(f"HTTP {status_code} for HEAD {endpoint}")
            raise ApiError(f"HTTP {status_code} for HEAD {endpoint}")
        envelope["exists"] = 200 <= status_code < 300
        return envelope

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "DockerHubApiBase":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

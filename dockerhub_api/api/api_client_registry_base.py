"""Base HTTP plumbing for the Registry HTTP API v2 client.

CONCEPT:HUB-1.7 — Registry v2 client + scoped-token auth. The registry
(``registry-1.docker.io``) is a *different* API and auth model than the
``hub.docker.com`` management API: every request is authorized by a
per-repository, per-action bearer obtained from a token service via a
``401 WWW-Authenticate`` challenge. This base reuses the shared
transport/retry/rate-limit/destructive-gating machinery from
:class:`~dockerhub_api.api.api_client_base.DockerHubApiBase` and adds the
scoped-token request engine on top.
"""

import time
from typing import Any

import httpx

from dockerhub_api.api.api_client_base import (
    JSON_CONTENT_TYPE,
    DockerHubApiBase,
)

#: ``Accept`` set that asks the registry for any modern manifest media type
#: (image manifest, manifest list, or OCI image/index). Sending all of these
#: lets the registry resolve multi-arch references to the right object.
ACCEPT_MANIFESTS = ",".join(
    (
        "application/vnd.docker.distribution.manifest.v2+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.oci.image.index.v1+json",
    )
)

OCTET_STREAM = "application/octet-stream"

#: Response headers surfaced into the envelope — needed for digest resolution
#: (``Docker-Content-Digest``) and upload-session tracking (``Location`` etc.).
_SURFACED_HEADERS = (
    "Docker-Content-Digest",
    "Content-Type",
    "Location",
    "Range",
    "OCI-Subject",
    "Docker-Upload-UUID",
)


class RegistryApiBase(DockerHubApiBase):
    """Shared Registry v2 transport with challenge-based scoped-token auth."""

    def __init__(
        self,
        url: str | None = None,
        registry_token_manager: Any | None = None,
        verify: bool = True,
        timeout: float | None = None,
        allow_destructive: bool = False,
        debug: bool = False,
        transport: httpx.BaseTransport | None = None,
        **kwargs: Any,
    ):
        from dockerhub_api.auth import DEFAULT_REGISTRY_URL

        super().__init__(
            url=url or DEFAULT_REGISTRY_URL,
            verify=verify,
            timeout=timeout if timeout is not None else 30.0,
            allow_destructive=allow_destructive,
            debug=debug,
            transport=transport,
            **kwargs,
        )
        self._registry_token_manager = registry_token_manager
        # The registry redirects blob reads to a CDN; follow those. httpx strips
        # the Authorization header on cross-origin redirects, so the scoped
        # token is never leaked to the storage backend.
        self._client.close()
        self._client = httpx.Client(
            base_url=self.url,
            verify=verify,
            timeout=self.timeout,
            transport=transport,
            follow_redirects=True,
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _normalize_repo(repo: str) -> str:
        """Expand a single-segment name to its ``library/`` official path."""
        repo = repo.strip("/")
        if "/" not in repo:
            return f"library/{repo}"
        return repo

    def _registry_headers(
        self,
        scope: str,
        realm: str | None,
        service: str | None,
        accept: str | None,
        content_type: str | None,
        extra_headers: dict[str, str] | None,
    ) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": accept or JSON_CONTENT_TYPE}
        if content_type:
            headers["Content-Type"] = content_type
        if self._registry_token_manager is not None:
            token = self._registry_token_manager.get_token(scope, realm, service)
            if token:
                headers["Authorization"] = f"Bearer {token}"
        if extra_headers:
            headers.update(extra_headers)
        return headers

    # ------------------------------------------------------------------ #
    # Request engine
    # ------------------------------------------------------------------ #

    def _registry_request(
        self,
        method: str,
        repo: str | None,
        suffix: str = "",
        *,
        scope_actions: str = "pull",
        accept: str | None = None,
        params: dict | None = None,
        json: Any | None = None,
        content: Any | None = None,
        content_type: str | None = None,
        extra_headers: dict[str, str] | None = None,
        raw_url: str | None = None,
        raise_for_status: bool = True,
    ) -> dict[str, Any]:
        """Issue one Registry v2 request, handling the scoped-token challenge.

        Envelope: ``{"status_code", "data", "rate_limit", "headers"}`` where
        ``headers`` carries the registry-significant response headers
        (digest, upload location, range). ``raw_url`` targets an arbitrary URL
        (e.g. an upload ``Location``) while still authorizing against ``repo``.
        """
        normalized = self._normalize_repo(repo) if repo else None
        if raw_url is not None:
            endpoint = raw_url
            scope = f"repository:{normalized}:{scope_actions}" if normalized else ""
        elif repo is None:
            endpoint = "/v2/"
            scope = ""
        else:
            endpoint = f"/v2/{normalized}{suffix}"
            scope = f"repository:{normalized}:{scope_actions}"

        if params:
            params = {k: v for k, v in params.items() if v is not None}

        attempts = 0
        rechallenged = False
        realm: str | None = None
        service: str | None = None
        while True:
            headers = self._registry_headers(
                scope, realm, service, accept, content_type, extra_headers
            )
            response = self._client.request(
                method=method,
                url=endpoint,
                params=params or None,
                json=json,
                content=content,
                headers=headers,
            )
            rate_limit = self._capture_rate_limit(response)

            if response.status_code == 429 and attempts < self.max_retries:
                attempts += 1
                delay = self._retry_after_seconds(response)
                if delay > 0:
                    time.sleep(delay)
                continue

            if (
                response.status_code == 401
                and self._registry_token_manager is not None
                and not rechallenged
            ):
                from dockerhub_api.auth import parse_www_authenticate

                rechallenged = True
                challenge = parse_www_authenticate(
                    response.headers.get("WWW-Authenticate", "")
                )
                realm = challenge.get("realm") or realm
                service = challenge.get("service") or service
                if challenge.get("scope"):
                    scope = challenge["scope"]
                self._registry_token_manager.invalidate(scope)
                continue

            break

        data = self._parse_body(response)
        if raise_for_status and response.status_code >= 400:
            self._raise_for_status(response, data)

        surfaced = {
            key: response.headers[key]
            for key in _SURFACED_HEADERS
            if key in response.headers
        }
        return {
            "status_code": response.status_code,
            "data": data,
            "rate_limit": rate_limit or dict(self.rate_limit),
            "headers": surfaced,
        }

    def _registry_exists(
        self, repo: str, suffix: str, *, accept: str | None = None
    ) -> dict[str, Any]:
        """HEAD helper that returns ``exists`` plus the surfaced headers."""
        envelope = self._registry_request(
            "HEAD", repo, suffix, accept=accept, raise_for_status=False
        )
        status_code = envelope["status_code"]
        if status_code not in (200, 404) and status_code >= 400:
            self._raise_for_status_only(repo, suffix, status_code)
        envelope["exists"] = 200 <= status_code < 300
        return envelope

    def _raise_for_status_only(self, repo: str, suffix: str, status_code: int) -> None:
        from agent_utilities.core.exceptions import (
            ApiError,
            AuthError,
            UnauthorizedError,
        )

        target = f"HEAD /v2/{repo}{suffix}"
        if status_code == 401:
            raise AuthError(f"HTTP {status_code} for {target}")
        if status_code == 403:
            raise UnauthorizedError(f"HTTP {status_code} for {target}")
        raise ApiError(f"HTTP {status_code} for {target}")

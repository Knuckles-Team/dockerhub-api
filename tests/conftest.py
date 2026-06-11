"""Shared fixtures: a mocked Docker Hub served over httpx.MockTransport.

No live Docker Hub calls are made anywhere in the suite.
"""

import base64
import json
import re
import time

import httpx
import pytest

from dockerhub_api.api_client import Api

BASE_URL = "https://hub.docker.com"


def make_jwt(exp: float | None = None, **claims) -> str:
    """Build an unsigned JWT-shaped token with the given claims."""
    header = {"alg": "none", "typ": "JWT"}
    payload: dict = {"username": "tester", "sub": "uuid-tester"}
    if exp is not None:
        payload["exp"] = int(exp)
    payload.update(claims)

    def b64(obj) -> str:
        raw = json.dumps(obj).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")

    return f"{b64(header)}.{b64(payload)}.signature"


class MockHub:
    """A scriptable in-memory Docker Hub for httpx.MockTransport."""

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.minted_tokens = 0
        self.token_ttl = 3600.0
        self.pending_429 = 0
        self.retry_after = "0"
        self.rate_remaining = 179

    # ------------------------------------------------------------------ #

    def _headers(self, extra: dict | None = None) -> dict:
        headers = {
            "X-RateLimit-Limit": "180",
            "X-RateLimit-Remaining": str(self.rate_remaining),
            "X-RateLimit-Reset": str(int(time.time()) + 60),
        }
        if extra:
            headers.update(extra)
        return headers

    def _json(self, status_code: int, data, content_type: str = "application/json"):
        return httpx.Response(
            status_code,
            content=json.dumps(data).encode("utf-8"),
            headers=self._headers({"Content-Type": content_type}),
        )

    def _empty(self, status_code: int = 204):
        return httpx.Response(status_code, headers=self._headers())

    @staticmethod
    def _body(request: httpx.Request) -> dict:
        if not request.content:
            return {}
        return json.loads(request.content.decode("utf-8"))

    # ------------------------------------------------------------------ #

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        method = request.method

        if path == "/v2/auth/token" and method == "POST":
            body = self._body(request)
            if body.get("secret") == "wrong-secret":
                return self._json(401, {"detail": "invalid credentials"})
            self.minted_tokens += 1
            return self._json(
                200, {"access_token": make_jwt(exp=time.time() + self.token_ttl)}
            )

        if self.pending_429 > 0:
            self.pending_429 -= 1
            return httpx.Response(
                429,
                content=json.dumps({"detail": "rate limited"}).encode("utf-8"),
                headers=self._headers(
                    {"Content-Type": "application/json", "Retry-After": self.retry_after}
                ),
            )

        route = self._route(path, method, request)
        if route is not None:
            return route
        return self._json(404, {"detail": f"not found: {method} {path}"})

    # ------------------------------------------------------------------ #

    def _route(self, path, method, request):  # noqa: PLR0911,PLR0912
        body = self._body(request) if request.content else {}
        params = dict(request.url.params)

        # ---- legacy login + 2FA ---- #
        if path == "/v2/users/login" and method == "POST":
            if body.get("username") == "totp-user":
                return self._json(
                    401,
                    {"detail": "OTP required", "login_2fa_token": "2fa-token-123"},
                )
            return self._json(200, {"token": make_jwt(exp=time.time() + 600)})
        if path == "/v2/users/2fa-login" and method == "POST":
            if body.get("code") == "000000":
                return self._json(401, {"detail": "invalid code"})
            return self._json(200, {"token": make_jwt(exp=time.time() + 600)})

        # ---- personal access tokens ---- #
        if path == "/v2/access-tokens":
            if method == "GET":
                return self._json(
                    200,
                    {
                        "count": 1,
                        "active_count": 1,
                        "results": [
                            {
                                "uuid": "pat-1",
                                "token_label": "ci",
                                "scopes": ["repo:read"],
                                "is_active": True,
                            }
                        ],
                    },
                )
            if method == "POST":
                return self._json(
                    201,
                    {
                        "uuid": "pat-2",
                        "token": "dckr_pat_PLAINTEXT",
                        "token_label": body.get("token_label"),
                        "scopes": body.get("scopes"),
                        "is_active": True,
                    },
                )
        match = re.fullmatch(r"/v2/access-tokens/([^/]+)", path)
        if match:
            uuid = match.group(1)
            if method == "GET":
                return self._json(
                    200, {"uuid": uuid, "token_label": "ci", "is_active": True}
                )
            if method == "PATCH":
                return self._json(200, {"uuid": uuid, **body})
            if method == "DELETE":
                return self._empty()

        # ---- org access tokens ---- #
        match = re.fullmatch(r"/v2/orgs/([^/]+)/access-tokens", path)
        if match:
            if method == "GET":
                return self._json(
                    200,
                    {"count": 1, "results": [{"id": "oat-1", "label": "release"}]},
                )
            if method == "POST":
                return self._json(
                    201, {"id": "oat-2", "token": "dckr_oat_PLAINTEXT", **body}
                )
        match = re.fullmatch(r"/v2/orgs/([^/]+)/access-tokens/([^/]+)", path)
        if match:
            token_id = match.group(2)
            if method == "GET":
                return self._json(200, {"id": token_id, "label": "release"})
            if method == "PATCH":
                return self._json(200, {"id": token_id, **body})
            if method == "DELETE":
                return self._empty()

        # ---- audit logs ---- #
        match = re.fullmatch(r"/v2/auditlogs/([^/]+)/actions", path)
        if match and method == "GET":
            return self._json(
                200, {"actions": {"repo": ["repo.tag.push", "repo.create"]}}
            )
        match = re.fullmatch(r"/v2/auditlogs/([^/]+)", path)
        if match and method == "GET":
            return self._json(
                200,
                {
                    "count": 1,
                    "logs": [
                        {
                            "account": match.group(1),
                            "action": params.get("action", "repo.create"),
                            "actor": params.get("actor", "tester"),
                            "timestamp": "2026-06-10T00:00:00Z",
                        }
                    ],
                },
            )

        # ---- org settings ---- #
        match = re.fullmatch(r"/v2/orgs/([^/]+)/settings", path)
        if match:
            if method == "GET":
                return self._json(
                    200,
                    {
                        "restricted_images": {
                            "enabled": False,
                            "allow_official_images": True,
                            "allow_verified_publishers": True,
                        }
                    },
                )
            if method == "PUT":
                return self._json(200, body)

        # ---- org members ---- #
        match = re.fullmatch(r"/v2/orgs/([^/]+)/members/export", path)
        if match and method == "GET":
            return httpx.Response(
                200,
                content=b"username,email\ntester,tester@example.com\n",
                headers=self._headers({"Content-Type": "text/csv"}),
            )
        match = re.fullmatch(r"/v2/orgs/([^/]+)/members/([^/]+)", path)
        if match:
            if method == "PUT":
                return self._json(
                    200, {"username": match.group(2), "role": body.get("role")}
                )
            if method == "DELETE":
                return self._empty()
        match = re.fullmatch(r"/v2/orgs/([^/]+)/members", path)
        if match and method == "GET":
            return self._json(
                200,
                {
                    "count": 2,
                    "results": [
                        {"username": "tester", "role": "owner"},
                        {"username": "dev", "role": "member"},
                    ],
                },
            )

        # ---- invites ---- #
        if path == "/v2/invites/bulk" and method == "POST":
            return self._json(202, body)
        match = re.fullmatch(r"/v2/invites/([^/]+)/resend", path)
        if match and method == "PATCH":
            return self._json(200, {"id": match.group(1), "status": "resent"})
        match = re.fullmatch(r"/v2/invites/([^/]+)", path)
        if match and method == "DELETE":
            return self._empty()
        match = re.fullmatch(r"/v2/orgs/([^/]+)/invites", path)
        if match and method == "GET":
            return self._json(
                200,
                {"count": 1, "results": [{"id": "inv-1", "invitee": "new@x.io"}]},
            )

        # ---- groups (teams) ---- #
        match = re.fullmatch(r"/v2/orgs/([^/]+)/groups/([^/]+)/members/([^/]+)", path)
        if match and method == "DELETE":
            return self._empty()
        match = re.fullmatch(r"/v2/orgs/([^/]+)/groups/([^/]+)/members", path)
        if match:
            if method == "GET":
                return self._json(
                    200, {"count": 1, "results": [{"username": "tester"}]}
                )
            if method == "POST":
                return self._json(200, {"username": body.get("member")})
        match = re.fullmatch(r"/v2/orgs/([^/]+)/groups/([^/]+)", path)
        if match:
            group_name = match.group(2)
            if method == "GET":
                return self._json(200, {"id": 7, "name": group_name})
            if method in ("PUT", "PATCH"):
                return self._json(200, {"id": 7, "name": group_name, **body})
            if method == "DELETE":
                return self._empty()
        match = re.fullmatch(r"/v2/orgs/([^/]+)/groups", path)
        if match:
            if method == "GET":
                return self._json(
                    200, {"count": 1, "results": [{"id": 7, "name": "platform"}]}
                )
            if method == "POST":
                return self._json(201, {"id": 8, **body})

        # ---- repositories ---- #
        match = re.fullmatch(
            r"/v2/namespaces/([^/]+)/repositories/([^/]+)/immutabletags/verify", path
        )
        if match and method == "POST":
            return self._json(
                200, {"enabled": True, "rules": body.get("rules"), "results": []}
            )
        match = re.fullmatch(
            r"/v2/namespaces/([^/]+)/repositories/([^/]+)/immutabletags", path
        )
        if match and method == "PATCH":
            return self._json(200, body)
        match = re.fullmatch(
            r"/v2/namespaces/([^/]+)/repositories/([^/]+)/tags/([^/]+)", path
        )
        if match:
            tag = match.group(3)
            if tag == "missing":
                return (
                    self._empty(404) if method == "HEAD" else self._json(404, {})
                )
            if method == "HEAD":
                return self._empty(200)
            if method == "GET":
                return self._json(
                    200, {"name": tag, "full_size": 123, "tag_status": "active"}
                )
        match = re.fullmatch(
            r"/v2/namespaces/([^/]+)/repositories/([^/]+)/tags", path
        )
        if match:
            if method == "HEAD":
                return self._empty(200)
            if method == "GET":
                return self._json(
                    200,
                    {
                        "count": 2,
                        "results": [{"name": "latest"}, {"name": "v1.0.0"}],
                    },
                )
        match = re.fullmatch(r"/v2/namespaces/([^/]+)/repositories/([^/]+)", path)
        if match:
            namespace, repo = match.groups()
            if repo == "missing":
                return (
                    self._empty(404) if method == "HEAD" else self._json(404, {})
                )
            if method == "HEAD":
                return self._empty(200)
            if method == "GET":
                return self._json(
                    200,
                    {"name": repo, "namespace": namespace, "is_private": False},
                )
        match = re.fullmatch(r"/v2/namespaces/([^/]+)/repositories", path)
        if match:
            if method == "GET":
                return self._json(
                    200,
                    {
                        "count": 1,
                        "results": [
                            {"name": "app", "namespace": match.group(1)}
                        ],
                    },
                )
            if method == "POST":
                return self._json(201, body)
        match = re.fullmatch(r"/v2/repositories/([^/]+)/([^/]+)/groups", path)
        if match and method == "POST":
            return self._json(200, body)

        # ---- SCIM 2.0 ---- #
        if path.startswith("/v2/scim/2.0/"):
            return self._scim_route(path, method, body, params)

        return None

    def _scim_route(self, path, method, body, params):
        scim = "application/scim+json"
        if path == "/v2/scim/2.0/ServiceProviderConfig" and method == "GET":
            return self._json(
                200,
                {
                    "schemas": [
                        "urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"
                    ],
                    "patch": {"supported": False},
                    "filter": {"supported": True, "maxResults": 200},
                },
                content_type=scim,
            )
        if path == "/v2/scim/2.0/ResourceTypes" and method == "GET":
            return self._json(
                200,
                {"totalResults": 1, "Resources": [{"id": "User", "name": "User"}]},
                content_type=scim,
            )
        match = re.fullmatch(r"/v2/scim/2.0/ResourceTypes/([^/]+)", path)
        if match and method == "GET":
            return self._json(
                200, {"id": match.group(1), "name": match.group(1)}, content_type=scim
            )
        if path == "/v2/scim/2.0/Schemas" and method == "GET":
            return self._json(
                200,
                {
                    "totalResults": 1,
                    "Resources": [
                        {"id": "urn:ietf:params:scim:schemas:core:2.0:User"}
                    ],
                },
                content_type=scim,
            )
        match = re.fullmatch(r"/v2/scim/2.0/Schemas/(.+)", path)
        if match and method == "GET":
            return self._json(200, {"id": match.group(1)}, content_type=scim)
        if path == "/v2/scim/2.0/Users":
            if method == "GET":
                return self._json(
                    200,
                    {
                        "schemas": [
                            "urn:ietf:params:scim:api:messages:2.0:ListResponse"
                        ],
                        "totalResults": 1,
                        "startIndex": int(params.get("startIndex", 1)),
                        "itemsPerPage": int(params.get("count", 50)),
                        "Resources": [
                            {"id": "scim-1", "userName": "jane@example.com"}
                        ],
                    },
                    content_type=scim,
                )
            if method == "POST":
                return self._json(201, {"id": "scim-2", **body}, content_type=scim)
        match = re.fullmatch(r"/v2/scim/2.0/Users/([^/]+)", path)
        if match:
            if method == "GET":
                return self._json(
                    200,
                    {"id": match.group(1), "userName": "jane@example.com"},
                    content_type=scim,
                )
            if method == "PUT":
                return self._json(
                    200, {"id": match.group(1), **body}, content_type=scim
                )
        return self._json(404, {"detail": "scim not found"}, content_type=scim)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def hub_env(monkeypatch):
    monkeypatch.setenv("DOCKERHUB_URL", BASE_URL)
    monkeypatch.setenv("DOCKERHUB_USERNAME", "tester")
    monkeypatch.setenv("DOCKERHUB_TOKEN", "dckr_pat_unit")
    monkeypatch.delenv("DOCKERHUB_JWT", raising=False)
    monkeypatch.delenv("DOCKERHUB_ALLOW_DESTRUCTIVE", raising=False)


@pytest.fixture
def hub() -> MockHub:
    return MockHub()


def make_api(hub: MockHub, **overrides) -> Api:
    options = {
        "url": BASE_URL,
        "username": "tester",
        "password": "dckr_pat_unit",
        "transport": httpx.MockTransport(hub.handler),
    }
    options.update(overrides)
    return Api(**options)


@pytest.fixture
def api(hub) -> Api:
    return make_api(hub)


@pytest.fixture
def api_destructive(hub) -> Api:
    return make_api(hub, allow_destructive=True)

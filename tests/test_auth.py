"""Auth flows: JWT mint/cache/refresh, deprecated login, 2FA, whoami."""

import time

import httpx
import pytest
from agent_utilities.core.exceptions import AuthError

from dockerhub_api.auth import TokenManager, decode_jwt_claims, get_client
from tests.conftest import BASE_URL, MockHub, make_api, make_jwt


def test_token_minted_once_and_cached(hub, api):
    api.get_repositories(namespace="acme")
    api.get_repositories(namespace="acme")
    api.get_repository(namespace="acme", repository="app")
    assert hub.minted_tokens == 1


def test_token_refreshed_before_expiry(hub):
    # Tokens expire in 30s; refresh skew is 60s -> every call re-mints.
    hub.token_ttl = 30.0
    api = make_api(hub)
    api.get_repositories(namespace="acme")
    api.get_repositories(namespace="acme")
    assert hub.minted_tokens == 2


def test_requests_carry_bearer_header(hub, api):
    api.get_repositories(namespace="acme")
    api_request = hub.requests[-1]
    assert api_request.headers["Authorization"].startswith("Bearer ")
    assert "eyJ" in api_request.headers["Authorization"]


def test_token_manager_rejects_bad_credentials(hub):
    manager = TokenManager(
        identifier="tester",
        secret="wrong-secret",
        url=BASE_URL,
        transport=httpx.MockTransport(hub.handler),
    )
    with pytest.raises(AuthError):
        manager.get_token()


def test_token_manager_invalidate_forces_remint(hub):
    manager = TokenManager(
        identifier="tester",
        secret="dckr_pat_unit",
        url=BASE_URL,
        transport=httpx.MockTransport(hub.handler),
    )
    manager.get_token()
    manager.invalidate()
    manager.get_token()
    assert hub.minted_tokens == 2


def test_decode_jwt_claims_roundtrip():
    token = make_jwt(exp=1234567890, username="alice")
    claims = decode_jwt_claims(token)
    assert claims["exp"] == 1234567890
    assert claims["username"] == "alice"


def test_decode_jwt_claims_tolerates_garbage():
    assert decode_jwt_claims("not-a-jwt") == {}
    assert decode_jwt_claims("a.%%%.c") == {}


def test_create_auth_token_endpoint(api):
    result = api.create_auth_token(identifier="tester", secret="dckr_pat_unit")
    assert result["status_code"] == 200
    assert result["data"]["access_token"].count(".") == 2


def test_legacy_login_is_deprecated_but_works(api):
    with pytest.deprecated_call():
        result = api.login(username="tester", password="hunter2")
    assert result["status_code"] == 200
    assert result["data"]["token"]


def test_legacy_login_surfaces_2fa_challenge(api):
    with pytest.deprecated_call():
        result = api.login(username="totp-user", password="hunter2")
    assert result["status_code"] == 401
    assert result["data"]["login_2fa_token"] == "2fa-token-123"


def test_two_factor_login_completes(api):
    result = api.two_factor_login(login_2fa_token="2fa-token-123", code="123456")
    assert result["status_code"] == 200
    assert result["data"]["token"]


def test_two_factor_login_invalid_code_raises(api):
    with pytest.raises(AuthError):
        api.two_factor_login(login_2fa_token="2fa-token-123", code="000000")


def test_expired_static_jwt_refresh_on_401(hub):
    """A 401 with a token manager triggers one transparent re-mint."""

    api = make_api(hub)
    # Pre-mint, then poison the cached token so the API returns 401 once.
    manager = api._token_manager
    assert manager is not None
    manager.get_token()
    manager._token = "stale-token"
    manager._expires_at = time.time() + 3600

    class Unauthorized(MockHub):
        def __init__(self, inner):
            super().__init__()
            self.inner = inner

        def handler(self, request):
            auth = request.headers.get("Authorization", "")
            if "stale-token" in auth:
                return self._json(401, {"detail": "JWT expired"})
            return self.inner.handler(request)

    wrapper = Unauthorized(hub)
    api._client = httpx.Client(
        base_url=BASE_URL, transport=httpx.MockTransport(wrapper.handler)
    )
    result = api.get_repositories(namespace="acme")
    assert result["status_code"] == 200
    assert hub.minted_tokens == 2  # initial + refresh after 401


def test_whoami_is_local_introspection(hub, api):
    api.get_repositories(namespace="acme")
    request_count = len(hub.requests)
    result = api.whoami()
    assert result["data"]["authenticated"] is True
    assert result["data"]["identity"] == "tester"
    assert "exp" in result["data"]["claims"]
    assert len(hub.requests) == request_count  # no network call


def test_whoami_static_token(hub):
    api = make_api(hub, username=None, password=None, token=make_jwt(exp=99999))
    result = api.whoami()
    assert result["data"]["authenticated"] is True
    assert result["data"]["identity"] == "tester"


def test_whoami_anonymous(hub):
    api = make_api(hub, username=None, password=None)
    result = api.whoami()
    assert result["data"]["authenticated"] is False


def test_get_client_prefers_jwt(monkeypatch):
    monkeypatch.setenv("DOCKERHUB_JWT", make_jwt(exp=99999))
    client = get_client()
    assert client._static_token is not None
    assert client._token_manager is None


def test_get_client_uses_token_manager(monkeypatch):
    client = get_client()
    assert client._token_manager is not None
    assert client._token_manager.identifier == "tester"


def test_get_client_destructive_env(monkeypatch):
    monkeypatch.setenv("DOCKERHUB_ALLOW_DESTRUCTIVE", "True")
    client = get_client()
    assert client.allow_destructive is True


def test_get_client_anonymous(monkeypatch):
    monkeypatch.delenv("DOCKERHUB_USERNAME", raising=False)
    monkeypatch.delenv("DOCKERHUB_TOKEN", raising=False)
    client = get_client()
    assert client._token_manager is None
    assert client._static_token is None


def test_legacy_login_hard_failure_raises(hub):
    """A login failure without a 2FA challenge maps to AuthError."""

    class Failing(MockHub):
        def _route(self, path, method, request):
            if path == "/v2/users/login":
                return self._json(403, {"detail": "account locked"})
            return super()._route(path, method, request)

    api = make_api(Failing())
    with pytest.deprecated_call(), pytest.raises(AuthError, match="account locked"):
        api.login(username="tester", password="hunter2")


def test_official_hub_tool_env_names_take_precedence(monkeypatch):
    """DOCKER_HUB_USER / DOCKER_HUB_TOKEN (official hub-tool names) are the
    primary credential env vars; legacy DOCKERHUB_* remain as fallbacks."""
    from dockerhub_api.auth import get_client

    monkeypatch.setenv("DOCKER_HUB_USER", "official-user")
    monkeypatch.setenv("DOCKER_HUB_TOKEN", "dckr_pat_official")
    monkeypatch.setenv("DOCKERHUB_USERNAME", "legacy-user")
    monkeypatch.setenv("DOCKERHUB_TOKEN", "dckr_pat_legacy")
    client = get_client()
    assert client._token_manager.identifier == "official-user"
    assert client._token_manager._secret == "dckr_pat_official"

    monkeypatch.delenv("DOCKER_HUB_USER")
    monkeypatch.delenv("DOCKER_HUB_TOKEN")
    client = get_client()
    assert client._token_manager.identifier == "legacy-user"

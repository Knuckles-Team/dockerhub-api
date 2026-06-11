"""Rate-limit header capture, 429 Retry-After backoff, error mapping."""

import httpx
import pytest
from agent_utilities.core.exceptions import (
    ApiError,
    AuthError,
    ParameterError,
    UnauthorizedError,
)

from tests.conftest import BASE_URL, make_api


def test_rate_limit_captured_in_envelope(hub, api):
    hub.rate_remaining = 42
    result = api.get_repositories(namespace="acme")
    assert result["rate_limit"]["limit"] == 180
    assert result["rate_limit"]["remaining"] == 42
    assert isinstance(result["rate_limit"]["reset"], int)


def test_rate_limit_snapshot_on_client(hub, api):
    hub.rate_remaining = 7
    api.get_repositories(namespace="acme")
    assert api.rate_limit["remaining"] == 7
    snapshot = api.get_rate_limit()
    assert snapshot["data"]["remaining"] == 7


def test_429_retries_then_succeeds(hub, api):
    hub.pending_429 = 2  # two 429s, then success
    result = api.get_repositories(namespace="acme")
    assert result["status_code"] == 200
    # 1 token mint + 2 rate-limited attempts + 1 success
    api_calls = [r for r in hub.requests if r.url.path != "/v2/auth/token"]
    assert len(api_calls) == 3


def test_429_exhausts_retries_and_raises(hub, api):
    hub.pending_429 = 10
    with pytest.raises(ApiError, match="rate limited"):
        api.get_repositories(namespace="acme")


def test_retry_after_is_bounded(hub):
    api = make_api(hub, retry_after_cap=0.0)
    hub.retry_after = "9999"  # would stall without the cap
    hub.pending_429 = 1
    result = api.get_repositories(namespace="acme")
    assert result["status_code"] == 200


def test_retry_after_garbage_header(hub):
    api = make_api(hub, retry_after_cap=0.0)
    hub.retry_after = "soon"
    hub.pending_429 = 1
    assert api.get_repositories(namespace="acme")["status_code"] == 200


def _static_api(status_code: int, payload: dict):
    """Build a client whose API responses always return one status/payload."""
    from dockerhub_api.api_client import Api

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v2/auth/token":
            return httpx.Response(200, json={"access_token": "x.y.z"})  # nosec B105 B106 — fake test credential
        return httpx.Response(status_code, json=payload)

    return Api(
        url=BASE_URL,
        username="tester",
        password="dckr_pat_unit",  # nosec B105 B106 — fake test credential
        transport=httpx.MockTransport(handler),
    )


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (400, ParameterError),
        (403, UnauthorizedError),
        (404, ParameterError),
        (409, ApiError),
        (500, ApiError),
    ],
)
def test_error_envelope_mapping(status_code, expected):
    api = _static_api(status_code, {"detail": "boom"})
    with pytest.raises(expected, match="boom"):
        api.get_repositories(namespace="acme")


def test_persistent_401_maps_to_auth_error():
    api = _static_api(401, {"detail": "bad token"})
    with pytest.raises(AuthError, match="bad token"):
        api.get_repositories(namespace="acme")

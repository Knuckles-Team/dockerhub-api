"""Api facade request/response behavior over the mocked transport
(CONCEPT:HUB-1.0): uniform envelope, bearer auth header, query params,
and destructive gating at the facade level."""

import pytest

from dockerhub_api.api.api_client_base import DestructiveOperationError
from dockerhub_api.api_client import Api


def test_envelope_shape(api):
    result = api.get_repositories(namespace="teamspace")
    assert set(result) >= {"status_code", "data", "rate_limit"}
    assert result["status_code"] == 200
    assert isinstance(result["data"], dict)


def test_requests_carry_bearer_jwt(hub, api):
    api.get_repositories(namespace="teamspace")
    data_requests = [r for r in hub.requests if r.url.path != "/v2/auth/token"]
    assert data_requests
    auth_header = data_requests[-1].headers.get("Authorization", "")
    assert auth_header.startswith("Bearer ")


def test_query_parameters_are_forwarded(hub, api):
    api.get_repositories(namespace="teamspace", page=2, page_size=5)
    request = hub.requests[-1]
    assert request.url.params["page"] == "2"
    assert request.url.params["page_size"] == "5"


def test_facade_composes_all_domain_mixins():
    for method in (
        "create_auth_token",
        "get_access_tokens",
        "get_org_access_tokens",
        "get_audit_logs",
        "get_org_settings",
        "get_repositories",
        "get_groups",
        "get_scim_users",
        "get_rate_limit",
        "whoami",
    ):
        assert callable(getattr(Api, method, None)), f"missing {method}"


def test_destructive_call_blocked_by_default(api):
    with pytest.raises(DestructiveOperationError):
        api.delete_access_token(uuid="uuid-1")


def test_destructive_call_allowed_when_enabled(api_destructive):
    result = api_destructive.delete_access_token(uuid="uuid-1")
    assert result["status_code"] in (200, 202, 204)

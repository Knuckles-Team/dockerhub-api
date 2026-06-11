"""PAT and OAT lifecycle, including destructive gating."""

import json

import pytest

from dockerhub_api.api.api_client_base import DestructiveOperationError


def test_list_pats_pagination(hub, api):
    result = api.get_access_tokens(page=1, page_size=10)
    assert result["data"]["results"][0]["uuid"] == "pat-1"
    assert dict(hub.requests[-1].url.params) == {"page": "1", "page_size": "10"}


def test_create_pat_scopes(hub, api):
    result = api.create_access_token(token_label="ci", scopes=["repo:read"])
    assert result["status_code"] == 201
    assert result["data"]["token"] == "dckr_pat_PLAINTEXT"
    assert json.loads(hub.requests[-1].content) == {
        "token_label": "ci",
        "scopes": ["repo:read"],
    }


def test_create_pat_rejects_invalid_scope(api):
    with pytest.raises(ValueError, match="Invalid PAT scopes"):
        api.create_access_token(token_label="ci", scopes=["repo:everything"])


def test_get_and_update_pat(hub, api):
    assert api.get_access_token(uuid="pat-1")["data"]["uuid"] == "pat-1"
    result = api.update_access_token(uuid="pat-1", is_active=False)
    assert result["data"]["is_active"] is False
    assert hub.requests[-1].method == "PATCH"


def test_update_pat_requires_a_change(api):
    with pytest.raises(ValueError, match="token_label and/or is_active"):
        api.update_access_token(uuid="pat-1")


def test_delete_pat_gated_by_default(api):
    with pytest.raises(DestructiveOperationError, match="delete_access_token"):
        api.delete_access_token(uuid="pat-1")


def test_delete_pat_allowed_when_enabled(hub, api_destructive):
    result = api_destructive.delete_access_token(uuid="pat-1")
    assert result["status_code"] == 204
    assert hub.requests[-1].method == "DELETE"


def test_list_oats(hub, api):
    result = api.get_org_access_tokens(org="acme", page=2, page_size=5)
    assert result["data"]["results"][0]["id"] == "oat-1"
    assert dict(hub.requests[-1].url.params) == {"page": "2", "page_size": "5"}


def test_create_oat_with_resources(hub, api):
    result = api.create_org_access_token(
        org="acme",
        label="release-bot",
        description="CI releases",
        expires_at="2027-01-01T00:00:00Z",
        resources=[
            {"type": "TYPE_REPO", "name": "acme/*", "scopes": ["repo:write"]},
            {"type": "TYPE_ORG", "scopes": ["org:read"]},
        ],
    )
    assert result["status_code"] == 201
    assert result["data"]["token"] == "dckr_oat_PLAINTEXT"
    body = json.loads(hub.requests[-1].content)
    assert body["label"] == "release-bot"
    assert body["expires_at"] == "2027-01-01T00:00:00Z"
    assert body["resources"][0]["type"] == "TYPE_REPO"


def test_create_oat_rejects_bad_resource_type(api):
    with pytest.raises(ValueError, match="resource type"):
        api.create_org_access_token(
            org="acme", label="x", resources=[{"type": "TYPE_TEAM"}]
        )


def test_get_update_oat(hub, api):
    assert api.get_org_access_token(org="acme", token_id="oat-1")["data"]["id"] == "oat-1"
    result = api.update_org_access_token(org="acme", token_id="oat-1", is_active=False)
    assert result["data"]["is_active"] is False


def test_delete_oat_gated(api, api_destructive, hub):
    with pytest.raises(DestructiveOperationError):
        api.delete_org_access_token(org="acme", token_id="oat-1")
    assert api_destructive.delete_org_access_token(org="acme", token_id="oat-1")[
        "status_code"
    ] == 204

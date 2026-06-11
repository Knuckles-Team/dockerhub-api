"""Groups (teams) and group membership."""

import json

import pytest

from dockerhub_api.api.api_client_base import DestructiveOperationError


def test_list_groups(hub, api):
    result = api.get_groups(org="acme", search="plat", page=1, page_size=10)
    assert result["data"]["results"][0]["name"] == "platform"
    assert dict(hub.requests[-1].url.params) == {
        "search": "plat",
        "page": "1",
        "page_size": "10",
    }


def test_create_group(hub, api):
    result = api.create_group(org="acme", name="platform", description="Infra team")
    assert result["status_code"] == 201
    assert json.loads(hub.requests[-1].content) == {
        "name": "platform",
        "description": "Infra team",
    }


def test_get_group(api):
    assert (
        api.get_group(org="acme", group_name="platform")["data"]["name"] == "platform"
    )


def test_update_and_patch_group(hub, api):
    api.update_group(org="acme", group_name="platform", description="Updated")
    assert hub.requests[-1].method == "PUT"
    api.patch_group(org="acme", group_name="platform", name="platform-eng")
    assert hub.requests[-1].method == "PATCH"


def test_update_group_requires_change(api):
    with pytest.raises(ValueError, match="name and/or description"):
        api.update_group(org="acme", group_name="platform")


def test_delete_group_gated(api, api_destructive):
    with pytest.raises(DestructiveOperationError):
        api.delete_group(org="acme", group_name="platform")
    assert (
        api_destructive.delete_group(org="acme", group_name="platform")["status_code"]
        == 204
    )


def test_group_members_roundtrip(hub, api, api_destructive):
    members = api.get_group_members(org="acme", group_name="platform")
    assert members["data"]["results"][0]["username"] == "tester"

    added = api.add_group_member(org="acme", group_name="platform", member="dev")
    assert added["data"]["username"] == "dev"

    with pytest.raises(DestructiveOperationError):
        api.remove_group_member(org="acme", group_name="platform", username="dev")
    removed = api_destructive.remove_group_member(
        org="acme", group_name="platform", username="dev"
    )
    assert removed["status_code"] == 204
    assert hub.requests[-1].url.path == "/v2/orgs/acme/groups/platform/members/dev"

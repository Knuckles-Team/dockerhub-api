"""Repositories, tags, immutable tags, and repo-team permissions."""

import json

import pytest
from agent_utilities.core.exceptions import ParameterError

from dockerhub_api.dockerhub_input_models import RepositoryCreateModel


def last_api_request(hub):
    return hub.requests[-1]


def test_list_repositories_with_filters(hub, api):
    result = api.get_repositories(
        namespace="acme", name="app", ordering="-last_updated", page=2, page_size=50
    )
    assert result["status_code"] == 200
    assert result["data"]["results"][0]["name"] == "app"
    params = dict(last_api_request(hub).url.params)
    assert params == {
        "name": "app",
        "ordering": "-last_updated",
        "page": "2",
        "page_size": "50",
    }


def test_list_repositories_rejects_bad_ordering(api):
    with pytest.raises(ValueError, match="ordering"):
        api.get_repositories(namespace="acme", ordering="newest")


def test_create_repository_payload(hub, api):
    result = api.create_repository(
        namespace="acme",
        name="release-images",
        description="Release artifacts",
        full_description="# Releases",
        is_private=True,
    )
    assert result["status_code"] == 201
    body = json.loads(last_api_request(hub).content)
    assert body == {
        "name": "release-images",
        "namespace": "acme",
        "registry": "docker",
        "is_private": True,
        "description": "Release artifacts",
        "full_description": "# Releases",
    }


def test_create_repository_rejects_invalid_name():
    with pytest.raises(ValueError, match="lowercase"):
        RepositoryCreateModel(namespace="acme", name="Bad_Name!")


def test_get_repository(api):
    result = api.get_repository(namespace="acme", repository="app")
    assert result["data"]["namespace"] == "acme"


def test_get_repository_not_found_raises(api):
    with pytest.raises(ParameterError):
        api.get_repository(namespace="acme", repository="missing")


def test_check_repository_exists(api):
    assert api.check_repository(namespace="acme", repository="app")["exists"] is True
    assert (
        api.check_repository(namespace="acme", repository="missing")["exists"] is False
    )


def test_list_tags_paginated(hub, api):
    result = api.get_repository_tags(
        namespace="acme", repository="app", page=3, page_size=25
    )
    assert [tag["name"] for tag in result["data"]["results"]] == ["latest", "v1.0.0"]
    params = dict(last_api_request(hub).url.params)
    assert params == {"page": "3", "page_size": "25"}


def test_get_single_tag(api):
    result = api.get_repository_tag(namespace="acme", repository="app", tag="v1.0.0")
    assert result["data"]["name"] == "v1.0.0"


def test_check_tag_head(api):
    assert (
        api.check_repository_tag(namespace="acme", repository="app", tag="latest")[
            "exists"
        ]
        is True
    )
    assert (
        api.check_repository_tag(namespace="acme", repository="app", tag="missing")[
            "exists"
        ]
        is False
    )
    assert api.check_repository_tags(namespace="acme", repository="app")["exists"]


def test_update_immutable_tags(hub, api):
    result = api.update_immutable_tags(
        namespace="acme", repository="app", enabled=True, rules=["v*"]
    )
    assert result["data"]["enabled"] is True
    assert last_api_request(hub).method == "PATCH"
    assert json.loads(last_api_request(hub).content) == {
        "enabled": True,
        "rules": ["v*"],
    }


def test_verify_immutable_tags(hub, api):
    result = api.verify_immutable_tags(
        namespace="acme", repository="app", rules=["v*", "release-*"]
    )
    assert result["status_code"] == 200
    assert result["data"]["rules"] == ["v*", "release-*"]
    assert last_api_request(hub).url.path.endswith("/immutabletags/verify")


def test_verify_immutable_tags_requires_input(api):
    with pytest.raises(ValueError, match="rules and/or tags"):
        api.verify_immutable_tags(namespace="acme", repository="app")


def test_assign_repository_group(hub, api):
    result = api.assign_repository_group(
        namespace="acme", repository="app", group_id=7, permission="write"
    )
    assert result["status_code"] == 200
    assert last_api_request(hub).url.path == "/v2/repositories/acme/app/groups"
    assert json.loads(last_api_request(hub).content) == {
        "group_id": 7,
        "permission": "write",
    }


def test_assign_repository_group_validates_permission(api):
    with pytest.raises(ValueError, match="permission"):
        api.assign_repository_group(
            namespace="acme", repository="app", group_id=7, permission="owner"
        )

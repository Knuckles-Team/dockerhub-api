"""SCIM 2.0: content-type handling, pagination, discovery, provisioning."""

import json

import pytest


def scim_requests(hub):
    return [r for r in hub.requests if r.url.path.startswith("/v2/scim/2.0/")]


def test_scim_content_type_headers(hub, api):
    api.get_scim_users()
    request = scim_requests(hub)[-1]
    assert request.headers["Accept"] == "application/scim+json"
    assert request.headers["Content-Type"] == "application/scim+json"


def test_scim_list_users_pagination(hub, api):
    result = api.get_scim_users(
        start_index=11,
        count=5,
        filter='userName eq "jane@example.com"',
        sort_by="userName",
        sort_order="descending",
    )
    assert result["data"]["startIndex"] == 11
    assert result["data"]["itemsPerPage"] == 5
    params = dict(scim_requests(hub)[-1].url.params)
    assert params == {
        "startIndex": "11",
        "count": "5",
        "filter": 'userName eq "jane@example.com"',
        "sortBy": "userName",
        "sortOrder": "descending",
    }


def test_scim_rejects_bad_sort_order(api):
    with pytest.raises(ValueError, match="sort order"):
        api.get_scim_users(sort_order="upwards")


def test_scim_service_provider_config(api):
    result = api.get_scim_service_provider_config()
    assert result["data"]["filter"]["supported"] is True


def test_scim_resource_types_and_schemas(api):
    assert api.get_scim_resource_types()["data"]["totalResults"] == 1
    assert api.get_scim_resource_type(name="User")["data"]["id"] == "User"
    assert api.get_scim_schemas()["data"]["totalResults"] == 1
    schema_id = "urn:ietf:params:scim:schemas:core:2.0:User"
    assert api.get_scim_schema(schema_id=schema_id)["data"]["id"] == schema_id


def test_scim_create_user_payload(hub, api):
    result = api.create_scim_user(
        user_name="jane@example.com", given_name="Jane", family_name="Doe"
    )
    assert result["status_code"] == 201
    body = json.loads(scim_requests(hub)[-1].content)
    assert body["schemas"] == ["urn:ietf:params:scim:schemas:core:2.0:User"]
    assert body["userName"] == "jane@example.com"
    assert body["name"] == {"givenName": "Jane", "familyName": "Doe"}
    assert body["emails"] == [{"value": "jane@example.com", "primary": True}]


def test_scim_get_and_replace_user(hub, api):
    assert api.get_scim_user(user_id="scim-1")["data"]["id"] == "scim-1"
    result = api.replace_scim_user(
        user_id="scim-1", user_name="jane@example.com", active=False
    )
    assert result["data"]["active"] is False
    request = scim_requests(hub)[-1]
    assert request.method == "PUT"
    assert json.loads(request.content)["id"] == "scim-1"

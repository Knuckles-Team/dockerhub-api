"""Org settings, members, exports, and invites."""

import json

import pytest

from dockerhub_api.api.api_client_base import DestructiveOperationError


def test_get_org_settings(api):
    result = api.get_org_settings(org="acme")
    assert result["data"]["restricted_images"]["enabled"] is False


def test_update_org_settings_gated(api):
    with pytest.raises(DestructiveOperationError, match="update_org_settings"):
        api.update_org_settings(org="acme", restricted_images_enabled=True)


def test_update_org_settings_payload(hub, api_destructive):
    result = api_destructive.update_org_settings(
        org="acme",
        restricted_images_enabled=True,
        allow_official_images=True,
        allow_verified_publishers=False,
    )
    assert result["status_code"] == 200
    assert json.loads(hub.requests[-1].content) == {
        "restricted_images": {
            "enabled": True,
            "allow_official_images": True,
            "allow_verified_publishers": False,
        }
    }


def test_list_members_filters(hub, api):
    result = api.get_org_members(
        org="acme",
        search="dev",
        member_type="member",
        role="member",
        page=1,
        page_size=25,
    )
    assert result["data"]["count"] == 2
    params = dict(hub.requests[-1].url.params)
    assert params == {
        "search": "dev",
        "type": "member",
        "role": "member",
        "page": "1",
        "page_size": "25",
    }


def test_list_members_rejects_bad_role(api):
    with pytest.raises(ValueError, match="role"):
        api.get_org_members(org="acme", role="superadmin")


def test_export_members_csv(hub, api):
    result = api.export_org_members(org="acme")
    assert result["status_code"] == 200
    assert "username,email" in result["data"]
    assert hub.requests[-1].headers["Accept"] == "text/csv"


def test_update_member_role(hub, api):
    result = api.update_org_member(org="acme", username="dev", role="editor")
    assert result["data"]["role"] == "editor"
    assert hub.requests[-1].method == "PUT"


def test_remove_member_gated(api, api_destructive):
    with pytest.raises(DestructiveOperationError):
        api.remove_org_member(org="acme", username="dev")
    assert (
        api_destructive.remove_org_member(org="acme", username="dev")["status_code"]
        == 204
    )


def test_list_invites(api):
    result = api.get_org_invites(org="acme")
    assert result["data"]["results"][0]["id"] == "inv-1"


def test_delete_invite_gated(api, api_destructive):
    with pytest.raises(DestructiveOperationError):
        api.delete_invite(invite_id="inv-1")
    assert api_destructive.delete_invite(invite_id="inv-1")["status_code"] == 204


def test_resend_invite(hub, api):
    result = api.resend_invite(invite_id="inv-1")
    assert result["data"]["status"] == "resent"
    assert hub.requests[-1].url.path == "/v2/invites/inv-1/resend"
    assert hub.requests[-1].method == "PATCH"


def test_bulk_invite_dry_run(hub, api):
    result = api.bulk_invite(
        org="acme",
        invitees=["new@x.io", "dev2"],
        team="platform",
        role="member",
        dry_run=True,
    )
    assert result["status_code"] == 202
    body = json.loads(hub.requests[-1].content)
    assert body == {
        "org": "acme",
        "invitees": ["new@x.io", "dev2"],
        "role": "member",
        "dry_run": True,
        "team": "platform",
    }
    assert result["data"]["dry_run"] is True


def test_bulk_invite_requires_invitees(api):
    with pytest.raises(ValueError, match="invitee"):
        api.bulk_invite(org="acme", invitees=[])

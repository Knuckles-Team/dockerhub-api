"""Group (team) endpoints (``/v2/orgs/{org}/groups``).

CONCEPT:HUB-1.0 — core wrapper.
CONCEPT:HUB-1.3 — destructive-action gating (group/member deletion).
"""

from typing import Any

from dockerhub_api.api.api_client_base import DockerHubApiBase
from dockerhub_api.dockerhub_input_models import (
    GroupCreateModel,
    GroupListModel,
    GroupMemberAddModel,
    GroupMemberListModel,
    GroupMemberModel,
    GroupModel,
    GroupUpdateModel,
)
from dockerhub_api.dockerhub_response_models import (
    Group,
    GroupPage,
    OrgMember,
    OrgMemberPage,
    validate_lenient,
)


class DockerHubApiGroups(DockerHubApiBase):
    """Org teams and their membership."""

    def get_groups(
        self,
        org: str,
        search: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        """List an organization's groups (teams)."""
        model = GroupListModel(org=org, search=search, page=page, page_size=page_size)
        envelope = self._request(
            "GET", f"/v2/orgs/{model.org}/groups", params=model.api_parameters
        )
        envelope["data"] = validate_lenient(GroupPage, envelope["data"])
        return envelope

    def create_group(
        self, org: str, name: str, description: str | None = None
    ) -> dict[str, Any]:
        """Create a group (team) in an organization."""
        model = GroupCreateModel(org=org, name=name, description=description)
        envelope = self._request(
            "POST", f"/v2/orgs/{model.org}/groups", json=model.payload
        )
        envelope["data"] = validate_lenient(Group, envelope["data"])
        return envelope

    def get_group(self, org: str, group_name: str) -> dict[str, Any]:
        """Get one group."""
        model = GroupModel(org=org, group_name=group_name)
        envelope = self._request(
            "GET", f"/v2/orgs/{model.org}/groups/{model.group_name}"
        )
        envelope["data"] = validate_lenient(Group, envelope["data"])
        return envelope

    def update_group(
        self,
        org: str,
        group_name: str,
        name: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Replace a group's details (``PUT``)."""
        model = GroupUpdateModel(
            org=org, group_name=group_name, name=name, description=description
        )
        envelope = self._request(
            "PUT", f"/v2/orgs/{model.org}/groups/{model.group_name}", json=model.payload
        )
        envelope["data"] = validate_lenient(Group, envelope["data"])
        return envelope

    def patch_group(
        self,
        org: str,
        group_name: str,
        name: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Partially update a group (``PATCH``)."""
        model = GroupUpdateModel(
            org=org, group_name=group_name, name=name, description=description
        )
        envelope = self._request(
            "PATCH",
            f"/v2/orgs/{model.org}/groups/{model.group_name}",
            json=model.payload,
        )
        envelope["data"] = validate_lenient(Group, envelope["data"])
        return envelope

    def delete_group(self, org: str, group_name: str) -> dict[str, Any]:
        """Delete a group. Destructive — gated."""
        self._guard_destructive("delete_group")
        model = GroupModel(org=org, group_name=group_name)
        return self._request(
            "DELETE", f"/v2/orgs/{model.org}/groups/{model.group_name}"
        )

    # ------------------------------ members ------------------------------ #

    def get_group_members(
        self,
        org: str,
        group_name: str,
        search: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        """List a group's members."""
        model = GroupMemberListModel(
            org=org,
            group_name=group_name,
            search=search,
            page=page,
            page_size=page_size,
        )
        envelope = self._request(
            "GET",
            f"/v2/orgs/{model.org}/groups/{model.group_name}/members",
            params=model.api_parameters,
        )
        envelope["data"] = validate_lenient(OrgMemberPage, envelope["data"])
        return envelope

    def add_group_member(
        self, org: str, group_name: str, member: str
    ) -> dict[str, Any]:
        """Add a username to a group."""
        model = GroupMemberAddModel(org=org, group_name=group_name, member=member)
        envelope = self._request(
            "POST",
            f"/v2/orgs/{model.org}/groups/{model.group_name}/members",
            json=model.payload,
        )
        envelope["data"] = validate_lenient(OrgMember, envelope["data"])
        return envelope

    def remove_group_member(
        self, org: str, group_name: str, username: str
    ) -> dict[str, Any]:
        """Remove a username from a group. Destructive — gated."""
        self._guard_destructive("remove_group_member")
        model = GroupMemberModel(org=org, group_name=group_name, username=username)
        return self._request(
            "DELETE",
            f"/v2/orgs/{model.org}/groups/{model.group_name}/members/{model.username}",
        )

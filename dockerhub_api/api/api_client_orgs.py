"""Organization endpoints: settings, members, and invites.

CONCEPT:DH-OS.audit.core-wrapper-api-is — core wrapper.
CONCEPT:DH-OS.identity.destructive-action-gating-member — destructive-action gating (member removal, invite deletion,
org-settings writes).
"""

from typing import Any

from dockerhub_api.api.api_client_base import DockerHubApiBase
from dockerhub_api.dockerhub_input_models import (
    BulkInviteModel,
    InviteModel,
    OrgMemberListModel,
    OrgMemberModel,
    OrgMemberUpdateModel,
    OrgSettingsModel,
)
from dockerhub_api.dockerhub_response_models import (
    BulkInviteResult,
    InvitePage,
    OrgMember,
    OrgMemberPage,
    OrgSettings,
    validate_lenient,
)


class DockerHubApiOrgs(DockerHubApiBase):
    """``/v2/orgs/{org}/settings``, ``/members``, and ``/v2/invites``."""

    # ----------------------------- settings ----------------------------- #

    def get_org_settings(self, org: str) -> dict[str, Any]:
        """Get an organization's settings (restricted images policy)."""
        envelope = self._request("GET", f"/v2/orgs/{org}/settings")
        envelope["data"] = validate_lenient(OrgSettings, envelope["data"])
        return envelope

    def update_org_settings(
        self,
        org: str,
        restricted_images_enabled: bool,
        allow_official_images: bool = True,
        allow_verified_publishers: bool = True,
    ) -> dict[str, Any]:
        """Replace an organization's settings. Destructive — gated.

        Controls ``restricted_images``: whether members may only pull
        org-approved images, with carve-outs for Docker Official Images and
        Verified Publisher images.
        """
        self._guard_destructive("update_org_settings")
        model = OrgSettingsModel(
            org=org,
            restricted_images_enabled=restricted_images_enabled,
            allow_official_images=allow_official_images,
            allow_verified_publishers=allow_verified_publishers,
        )
        envelope = self._request(
            "PUT", f"/v2/orgs/{model.org}/settings", json=model.payload
        )
        envelope["data"] = validate_lenient(OrgSettings, envelope["data"])
        return envelope

    # ----------------------------- members ------------------------------ #

    def get_org_members(
        self,
        org: str,
        search: str | None = None,
        member_type: str | None = None,
        role: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        """List organization members (filter by search/type/role; paginated)."""
        model = OrgMemberListModel(
            org=org,
            search=search,
            member_type=member_type,
            role=role,
            page=page,
            page_size=page_size,
        )
        envelope = self._request(
            "GET", f"/v2/orgs/{model.org}/members", params=model.api_parameters
        )
        envelope["data"] = validate_lenient(OrgMemberPage, envelope["data"])
        return envelope

    def export_org_members(self, org: str) -> dict[str, Any]:
        """Export the member list as CSV (``GET /members/export``)."""
        return self._request("GET", f"/v2/orgs/{org}/members/export", accept="text/csv")

    def update_org_member(self, org: str, username: str, role: str) -> dict[str, Any]:
        """Set a member's org role (``owner``, ``editor``, or ``member``)."""
        model = OrgMemberUpdateModel(org=org, username=username, role=role)
        envelope = self._request(
            "PUT",
            f"/v2/orgs/{model.org}/members/{model.username}",
            json=model.payload,
        )
        envelope["data"] = validate_lenient(OrgMember, envelope["data"])
        return envelope

    def remove_org_member(self, org: str, username: str) -> dict[str, Any]:
        """Remove a member from the organization. Destructive — gated."""
        self._guard_destructive("remove_org_member")
        model = OrgMemberModel(org=org, username=username)
        return self._request("DELETE", f"/v2/orgs/{model.org}/members/{model.username}")

    # ----------------------------- invites ------------------------------ #

    def get_org_invites(self, org: str) -> dict[str, Any]:
        """List an organization's pending invites."""
        envelope = self._request("GET", f"/v2/orgs/{org}/invites")
        envelope["data"] = validate_lenient(InvitePage, envelope["data"])
        return envelope

    def delete_invite(self, invite_id: str) -> dict[str, Any]:
        """Cancel an invite. Destructive — gated."""
        self._guard_destructive("delete_invite")
        model = InviteModel(invite_id=invite_id)
        return self._request("DELETE", f"/v2/invites/{model.invite_id}")

    def resend_invite(self, invite_id: str) -> dict[str, Any]:
        """Resend an invite (``PATCH /v2/invites/{id}/resend``)."""
        model = InviteModel(invite_id=invite_id)
        return self._request("PATCH", f"/v2/invites/{model.invite_id}/resend")

    def bulk_invite(
        self,
        org: str,
        invitees: list[str],
        team: str | None = None,
        role: str = "member",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Invite many users/emails at once (``POST /v2/invites/bulk``).

        ``dry_run=True`` validates the invitees without sending invites.
        """
        model = BulkInviteModel(
            org=org, invitees=invitees, team=team, role=role, dry_run=dry_run
        )
        envelope = self._request("POST", "/v2/invites/bulk", json=model.payload)
        envelope["data"] = validate_lenient(BulkInviteResult, envelope["data"])
        return envelope

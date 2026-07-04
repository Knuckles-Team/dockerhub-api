"""Organization access token (OAT) endpoints (``/v2/orgs/{org}/access-tokens``).

CONCEPT:DH-OS.identity.jwt-auth-lifecycle-endpoint — JWT auth lifecycle (OAT management).
"""

from typing import Any

from dockerhub_api.api.api_client_base import DockerHubApiBase
from dockerhub_api.dockerhub_input_models import (
    OrgAccessTokenCreateModel,
    OrgAccessTokenListModel,
    OrgAccessTokenModel,
    OrgAccessTokenPatchModel,
)
from dockerhub_api.dockerhub_response_models import (
    OrgAccessToken,
    OrgAccessTokenPage,
    validate_lenient,
)


class DockerHubApiOrgAccessTokens(DockerHubApiBase):
    """CRUD for organization access tokens."""

    def get_org_access_tokens(
        self, org: str, page: int | None = None, page_size: int | None = None
    ) -> dict[str, Any]:
        """List an organization's access tokens."""
        model = OrgAccessTokenListModel(org=org, page=page, page_size=page_size)
        envelope = self._request(
            "GET",
            f"/v2/orgs/{model.org}/access-tokens",
            params=model.api_parameters,
        )
        envelope["data"] = validate_lenient(OrgAccessTokenPage, envelope["data"])
        return envelope

    def create_org_access_token(
        self,
        org: str,
        label: str,
        description: str | None = None,
        expires_at: str | None = None,
        scopes: list[str] | None = None,
        resources: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Create an organization access token.

        ``resources`` entries scope the token to ``TYPE_REPO`` / ``TYPE_ORG``
        resources with path globs and per-resource scopes. The plaintext token
        is only returned once, in this response.
        """
        model = OrgAccessTokenCreateModel(
            org=org,
            label=label,
            description=description,
            expires_at=expires_at,
            scopes=scopes,
            resources=resources,
        )
        envelope = self._request(
            "POST", f"/v2/orgs/{model.org}/access-tokens", json=model.payload
        )
        envelope["data"] = validate_lenient(OrgAccessToken, envelope["data"])
        return envelope

    def get_org_access_token(self, org: str, token_id: str) -> dict[str, Any]:
        """Get one organization access token by id."""
        model = OrgAccessTokenModel(org=org, token_id=token_id)
        envelope = self._request(
            "GET", f"/v2/orgs/{model.org}/access-tokens/{model.token_id}"
        )
        envelope["data"] = validate_lenient(OrgAccessToken, envelope["data"])
        return envelope

    def update_org_access_token(
        self,
        org: str,
        token_id: str,
        label: str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any]:
        """Patch an organization access token."""
        model = OrgAccessTokenPatchModel(
            org=org,
            token_id=token_id,
            label=label,
            description=description,
            is_active=is_active,
        )
        envelope = self._request(
            "PATCH",
            f"/v2/orgs/{model.org}/access-tokens/{model.token_id}",
            json=model.payload,
        )
        envelope["data"] = validate_lenient(OrgAccessToken, envelope["data"])
        return envelope

    def delete_org_access_token(self, org: str, token_id: str) -> dict[str, Any]:
        """Delete an organization access token. Destructive — gated."""
        self._guard_destructive("delete_org_access_token")
        model = OrgAccessTokenModel(org=org, token_id=token_id)
        return self._request(
            "DELETE", f"/v2/orgs/{model.org}/access-tokens/{model.token_id}"
        )

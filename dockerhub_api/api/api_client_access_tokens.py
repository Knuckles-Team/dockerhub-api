"""Personal access token endpoints (``/v2/access-tokens``).

CONCEPT:DH-OS.identity.jwt-auth-lifecycle-endpoint — JWT auth lifecycle (PAT management).
"""

from typing import Any

from dockerhub_api.api.api_client_base import DockerHubApiBase
from dockerhub_api.dockerhub_input_models import (
    AccessTokenCreateModel,
    AccessTokenListModel,
    AccessTokenModel,
    AccessTokenPatchModel,
)
from dockerhub_api.dockerhub_response_models import (
    AccessToken,
    AccessTokenPage,
    validate_lenient,
)


class DockerHubApiAccessTokens(DockerHubApiBase):
    """CRUD for personal access tokens."""

    def get_access_tokens(
        self, page: int | None = None, page_size: int | None = None
    ) -> dict[str, Any]:
        """List the personal access tokens of the authenticated user."""
        model = AccessTokenListModel(page=page, page_size=page_size)
        envelope = self._request(
            "GET", "/v2/access-tokens", params=model.api_parameters
        )
        envelope["data"] = validate_lenient(AccessTokenPage, envelope["data"])
        return envelope

    def create_access_token(
        self, token_label: str, scopes: list[str]
    ) -> dict[str, Any]:
        """Create a personal access token.

        Valid scopes: ``repo:admin``, ``repo:write``, ``repo:read``,
        ``repo:public_read``. The plaintext token is only returned once,
        in this response.
        """
        model = AccessTokenCreateModel(token_label=token_label, scopes=scopes)
        envelope = self._request("POST", "/v2/access-tokens", json=model.payload)
        envelope["data"] = validate_lenient(AccessToken, envelope["data"])
        return envelope

    def get_access_token(self, uuid: str) -> dict[str, Any]:
        """Get one personal access token by UUID."""
        model = AccessTokenModel(uuid=uuid)
        envelope = self._request("GET", f"/v2/access-tokens/{model.uuid}")
        envelope["data"] = validate_lenient(AccessToken, envelope["data"])
        return envelope

    def update_access_token(
        self,
        uuid: str,
        token_label: str | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any]:
        """Patch a personal access token's label and/or active state."""
        model = AccessTokenPatchModel(
            uuid=uuid, token_label=token_label, is_active=is_active
        )
        envelope = self._request(
            "PATCH", f"/v2/access-tokens/{model.uuid}", json=model.payload
        )
        envelope["data"] = validate_lenient(AccessToken, envelope["data"])
        return envelope

    def delete_access_token(self, uuid: str) -> dict[str, Any]:
        """Delete a personal access token. Destructive — gated."""
        self._guard_destructive("delete_access_token")
        model = AccessTokenModel(uuid=uuid)
        return self._request("DELETE", f"/v2/access-tokens/{model.uuid}")

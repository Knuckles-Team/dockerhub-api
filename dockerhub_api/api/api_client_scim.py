"""SCIM 2.0 endpoints (``/v2/scim/2.0``).

CONCEPT:DH-OS.governance.scim-provisioning-all-requests — SCIM provisioning. All requests/responses use the
``application/scim+json`` media type and SCIM-style 1-based pagination
(``startIndex``/``count``).
"""

from typing import Any

from dockerhub_api.api.api_client_base import SCIM_CONTENT_TYPE, DockerHubApiBase
from dockerhub_api.dockerhub_input_models import (
    ScimUserCreateModel,
    ScimUserListModel,
    ScimUserModel,
    ScimUserReplaceModel,
)
from dockerhub_api.dockerhub_response_models import (
    ScimListResponse,
    ScimResourceType,
    ScimSchema,
    ScimServiceProviderConfig,
    ScimUser,
    validate_lenient,
)

SCIM_BASE = "/v2/scim/2.0"


class DockerHubApiScim(DockerHubApiBase):
    """SCIM service discovery and user provisioning."""

    def _scim_request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        json: Any | None = None,
    ) -> dict[str, Any]:
        return self._request(
            method,
            endpoint,
            params=params,
            json=json,
            content_type=SCIM_CONTENT_TYPE,
            accept=SCIM_CONTENT_TYPE,
        )

    # ----------------------------- discovery ----------------------------- #

    def get_scim_service_provider_config(self) -> dict[str, Any]:
        """Get the SCIM ServiceProviderConfig."""
        envelope = self._scim_request("GET", f"{SCIM_BASE}/ServiceProviderConfig")
        envelope["data"] = validate_lenient(ScimServiceProviderConfig, envelope["data"])
        return envelope

    def get_scim_resource_types(self) -> dict[str, Any]:
        """List the SCIM ResourceTypes."""
        envelope = self._scim_request("GET", f"{SCIM_BASE}/ResourceTypes")
        envelope["data"] = validate_lenient(ScimListResponse, envelope["data"])
        return envelope

    def get_scim_resource_type(self, name: str) -> dict[str, Any]:
        """Get one SCIM ResourceType by name."""
        envelope = self._scim_request("GET", f"{SCIM_BASE}/ResourceTypes/{name}")
        envelope["data"] = validate_lenient(ScimResourceType, envelope["data"])
        return envelope

    def get_scim_schemas(self) -> dict[str, Any]:
        """List the SCIM Schemas."""
        envelope = self._scim_request("GET", f"{SCIM_BASE}/Schemas")
        envelope["data"] = validate_lenient(ScimListResponse, envelope["data"])
        return envelope

    def get_scim_schema(self, schema_id: str) -> dict[str, Any]:
        """Get one SCIM Schema by id (URN)."""
        envelope = self._scim_request("GET", f"{SCIM_BASE}/Schemas/{schema_id}")
        envelope["data"] = validate_lenient(ScimSchema, envelope["data"])
        return envelope

    # ------------------------------- users ------------------------------- #

    def get_scim_users(
        self,
        start_index: int | None = None,
        count: int | None = None,
        filter: str | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> dict[str, Any]:
        """List SCIM users (``startIndex``/``count``/``filter``/``sortBy``/``sortOrder``)."""
        model = ScimUserListModel(
            start_index=start_index,
            count=count,
            filter=filter,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        envelope = self._scim_request(
            "GET", f"{SCIM_BASE}/Users", params=model.api_parameters
        )
        envelope["data"] = validate_lenient(ScimListResponse, envelope["data"])
        return envelope

    def create_scim_user(
        self,
        user_name: str,
        given_name: str | None = None,
        family_name: str | None = None,
        email: str | None = None,
        active: bool = True,
    ) -> dict[str, Any]:
        """Provision a SCIM user."""
        model = ScimUserCreateModel(
            user_name=user_name,
            given_name=given_name,
            family_name=family_name,
            email=email,
            active=active,
        )
        envelope = self._scim_request("POST", f"{SCIM_BASE}/Users", json=model.payload)
        envelope["data"] = validate_lenient(ScimUser, envelope["data"])
        return envelope

    def get_scim_user(self, user_id: str) -> dict[str, Any]:
        """Get one SCIM user by id."""
        model = ScimUserModel(user_id=user_id)
        envelope = self._scim_request("GET", f"{SCIM_BASE}/Users/{model.user_id}")
        envelope["data"] = validate_lenient(ScimUser, envelope["data"])
        return envelope

    def replace_scim_user(
        self,
        user_id: str,
        user_name: str,
        given_name: str | None = None,
        family_name: str | None = None,
        email: str | None = None,
        active: bool = True,
    ) -> dict[str, Any]:
        """Replace a SCIM user resource (``PUT``)."""
        model = ScimUserReplaceModel(
            user_id=user_id,
            user_name=user_name,
            given_name=given_name,
            family_name=family_name,
            email=email,
            active=active,
        )
        envelope = self._scim_request(
            "PUT", f"{SCIM_BASE}/Users/{model.user_id}", json=model.payload
        )
        envelope["data"] = validate_lenient(ScimUser, envelope["data"])
        return envelope

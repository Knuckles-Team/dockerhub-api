"""Pydantic input models for the Docker Hub API client.

CONCEPT:HUB-1.0 — core wrapper.

Each model validates the caller-supplied arguments for one endpoint family
and builds the query parameters (``api_parameters``) and/or request body
(``payload``) in ``model_post_init``, mirroring the gitlab-api convention.
"""

from pydantic import BaseModel, Field, field_validator, model_validator

PAT_SCOPES = {"repo:admin", "repo:write", "repo:read", "repo:public_read"}
OAT_RESOURCE_TYPES = {"TYPE_REPO", "TYPE_ORG"}
REPOSITORY_ORDERING = {
    "name",
    "-name",
    "last_updated",
    "-last_updated",
    "pull_count",
    "-pull_count",
}
ORG_ROLES = {"owner", "editor", "member"}
REPOSITORY_PERMISSIONS = {"read", "write", "admin"}
SCIM_SORT_ORDERS = {"ascending", "descending"}


class _PaginatedModel(BaseModel):
    """Shared ``page`` / ``page_size`` query-parameter handling."""

    page: int | None = Field(default=None, description="Pagination page", ge=1)
    page_size: int | None = Field(
        default=None, description="Results per page", ge=1, le=100
    )
    api_parameters: dict | None = Field(description="API parameters", default=None)

    def model_post_init(self, _context):
        self.api_parameters = {}
        if self.page is not None:
            self.api_parameters["page"] = self.page
        if self.page_size is not None:
            self.api_parameters["page_size"] = self.page_size


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #


class AuthTokenModel(BaseModel):
    """``POST /v2/auth/token`` — mint a short-lived JWT bearer."""

    identifier: str = Field(description="Username or organization name")
    secret: str = Field(description="Password, PAT (dckr_pat_*), or org token")
    payload: dict | None = Field(description="Request body", default=None)

    def model_post_init(self, _context):
        self.payload = {"identifier": self.identifier, "secret": self.secret}


class LoginModel(BaseModel):
    """``POST /v2/users/login`` (deprecated first-factor login)."""

    username: str
    password: str
    payload: dict | None = Field(description="Request body", default=None)

    def model_post_init(self, _context):
        self.payload = {"username": self.username, "password": self.password}


class TwoFactorLoginModel(BaseModel):
    """``POST /v2/users/2fa-login`` (TOTP second factor)."""

    login_2fa_token: str = Field(description="Token returned by the login call")
    code: str = Field(description="TOTP code from the authenticator app")
    payload: dict | None = Field(description="Request body", default=None)

    def model_post_init(self, _context):
        self.payload = {"login_2fa_token": self.login_2fa_token, "code": self.code}


# --------------------------------------------------------------------------- #
# Personal access tokens
# --------------------------------------------------------------------------- #


class AccessTokenListModel(_PaginatedModel):
    """``GET /v2/access-tokens``."""


class AccessTokenCreateModel(BaseModel):
    """``POST /v2/access-tokens``."""

    token_label: str = Field(description="Human-readable token label")
    scopes: list[str] = Field(description="Token scopes")
    payload: dict | None = Field(description="Request body", default=None)

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, value: list[str]) -> list[str]:
        invalid = sorted(set(value) - PAT_SCOPES)
        if invalid:
            raise ValueError(
                f"Invalid PAT scopes {invalid}; valid scopes: {sorted(PAT_SCOPES)}"
            )
        if not value:
            raise ValueError("At least one scope is required")
        return value

    def model_post_init(self, _context):
        self.payload = {"token_label": self.token_label, "scopes": self.scopes}


class AccessTokenModel(BaseModel):
    """``GET|DELETE /v2/access-tokens/{uuid}``."""

    uuid: str = Field(description="Access token UUID")


class AccessTokenPatchModel(BaseModel):
    """``PATCH /v2/access-tokens/{uuid}``."""

    uuid: str = Field(description="Access token UUID")
    token_label: str | None = None
    is_active: bool | None = None
    payload: dict | None = Field(description="Request body", default=None)

    @model_validator(mode="after")
    def validate_any_change(self):
        if self.token_label is None and self.is_active is None:
            raise ValueError("Provide token_label and/or is_active to update")
        return self

    def model_post_init(self, _context):
        self.payload = {}
        if self.token_label is not None:
            self.payload["token_label"] = self.token_label
        if self.is_active is not None:
            self.payload["is_active"] = self.is_active


# --------------------------------------------------------------------------- #
# Organization access tokens
# --------------------------------------------------------------------------- #


class OrgAccessTokenListModel(_PaginatedModel):
    """``GET /v2/orgs/{org}/access-tokens``."""

    org: str = Field(description="Organization name")


class OrgAccessTokenCreateModel(BaseModel):
    """``POST /v2/orgs/{org}/access-tokens``."""

    org: str = Field(description="Organization name")
    label: str = Field(description="Token label")
    description: str | None = None
    expires_at: str | None = Field(
        default=None, description="RFC 3339 expiry timestamp"
    )
    scopes: list[str] | None = Field(
        default=None, description="Org-wide scopes for the token"
    )
    resources: list[dict] | None = Field(
        default=None,
        description=(
            "Scoped resources: [{'type': 'TYPE_REPO'|'TYPE_ORG', "
            "'name': '<path glob>', 'scopes': [...]}]"
        ),
    )
    payload: dict | None = Field(description="Request body", default=None)

    @field_validator("resources")
    @classmethod
    def validate_resources(cls, value: list[dict] | None) -> list[dict] | None:
        if value is None:
            return value
        for resource in value:
            resource_type = resource.get("type")
            if resource_type not in OAT_RESOURCE_TYPES:
                raise ValueError(
                    f"Invalid resource type {resource_type!r}; "
                    f"valid types: {sorted(OAT_RESOURCE_TYPES)}"
                )
        return value

    def model_post_init(self, _context):
        self.payload = {"label": self.label}
        if self.description is not None:
            self.payload["description"] = self.description
        if self.expires_at is not None:
            self.payload["expires_at"] = self.expires_at
        if self.scopes is not None:
            self.payload["scopes"] = self.scopes
        if self.resources is not None:
            self.payload["resources"] = self.resources


class OrgAccessTokenModel(BaseModel):
    """``GET|DELETE /v2/orgs/{org}/access-tokens/{id}``."""

    org: str = Field(description="Organization name")
    token_id: str = Field(description="Org access token identifier")


class OrgAccessTokenPatchModel(BaseModel):
    """``PATCH /v2/orgs/{org}/access-tokens/{id}``."""

    org: str = Field(description="Organization name")
    token_id: str = Field(description="Org access token identifier")
    label: str | None = None
    description: str | None = None
    is_active: bool | None = None
    payload: dict | None = Field(description="Request body", default=None)

    @model_validator(mode="after")
    def validate_any_change(self):
        if self.label is None and self.description is None and self.is_active is None:
            raise ValueError("Provide label, description, and/or is_active to update")
        return self

    def model_post_init(self, _context):
        self.payload = {}
        if self.label is not None:
            self.payload["label"] = self.label
        if self.description is not None:
            self.payload["description"] = self.description
        if self.is_active is not None:
            self.payload["is_active"] = self.is_active


# --------------------------------------------------------------------------- #
# Audit logs
# --------------------------------------------------------------------------- #


class AuditLogModel(_PaginatedModel):
    """``GET /v2/auditlogs/{account}``."""

    account: str = Field(description="Namespace (user or organization)")
    action: str | None = Field(default=None, description="Filter by action name")
    name: str | None = Field(default=None, description="Filter by object name")
    actor: str | None = Field(default=None, description="Filter by actor username")
    from_date: str | None = Field(
        default=None, description="Window start (RFC 3339), sent as 'from'"
    )
    to_date: str | None = Field(
        default=None, description="Window end (RFC 3339), sent as 'to'"
    )

    def model_post_init(self, _context):
        super().model_post_init(_context)
        assert self.api_parameters is not None
        if self.action:
            self.api_parameters["action"] = self.action
        if self.name:
            self.api_parameters["name"] = self.name
        if self.actor:
            self.api_parameters["actor"] = self.actor
        if self.from_date:
            self.api_parameters["from"] = self.from_date
        if self.to_date:
            self.api_parameters["to"] = self.to_date


# --------------------------------------------------------------------------- #
# Organization settings, members, and invites
# --------------------------------------------------------------------------- #


class OrgSettingsModel(BaseModel):
    """``PUT /v2/orgs/{name}/settings``."""

    org: str = Field(description="Organization name")
    restricted_images_enabled: bool = Field(
        description="Enable image-pull restrictions for the organization"
    )
    allow_official_images: bool = Field(
        default=True, description="Allow Docker Official Images when restricted"
    )
    allow_verified_publishers: bool = Field(
        default=True, description="Allow Verified Publisher images when restricted"
    )
    payload: dict | None = Field(description="Request body", default=None)

    def model_post_init(self, _context):
        self.payload = {
            "restricted_images": {
                "enabled": self.restricted_images_enabled,
                "allow_official_images": self.allow_official_images,
                "allow_verified_publishers": self.allow_verified_publishers,
            }
        }


class OrgMemberListModel(_PaginatedModel):
    """``GET /v2/orgs/{org}/members``."""

    org: str = Field(description="Organization name")
    search: str | None = Field(default=None, description="Search by username/email")
    member_type: str | None = Field(
        default=None, description="Filter by membership type, sent as 'type'"
    )
    role: str | None = Field(default=None, description="Filter by role")

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str | None) -> str | None:
        if value is not None and value not in ORG_ROLES:
            raise ValueError(
                f"Invalid role {value!r}; valid roles: {sorted(ORG_ROLES)}"
            )
        return value

    def model_post_init(self, _context):
        super().model_post_init(_context)
        assert self.api_parameters is not None
        if self.search:
            self.api_parameters["search"] = self.search
        if self.member_type:
            self.api_parameters["type"] = self.member_type
        if self.role:
            self.api_parameters["role"] = self.role


class OrgMemberUpdateModel(BaseModel):
    """``PUT /v2/orgs/{org}/members/{username}``."""

    org: str
    username: str
    role: str = Field(description="New role: owner, editor, or member")
    payload: dict | None = Field(description="Request body", default=None)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if value not in ORG_ROLES:
            raise ValueError(
                f"Invalid role {value!r}; valid roles: {sorted(ORG_ROLES)}"
            )
        return value

    def model_post_init(self, _context):
        self.payload = {"role": self.role}


class OrgMemberModel(BaseModel):
    """``DELETE /v2/orgs/{org}/members/{username}``."""

    org: str
    username: str


class InviteModel(BaseModel):
    """``DELETE /v2/invites/{id}`` and ``PATCH /v2/invites/{id}/resend``."""

    invite_id: str = Field(description="Invite identifier")


class BulkInviteModel(BaseModel):
    """``POST /v2/invites/bulk``."""

    org: str = Field(description="Organization name")
    invitees: list[str] = Field(description="Usernames or email addresses to invite")
    team: str | None = Field(default=None, description="Team (group) to invite into")
    role: str = Field(default="member", description="Org role for the invitees")
    dry_run: bool = Field(default=False, description="Validate without sending")
    payload: dict | None = Field(description="Request body", default=None)

    @field_validator("invitees")
    @classmethod
    def validate_invitees(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("At least one invitee is required")
        return value

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if value not in ORG_ROLES:
            raise ValueError(
                f"Invalid role {value!r}; valid roles: {sorted(ORG_ROLES)}"
            )
        return value

    def model_post_init(self, _context):
        self.payload = {
            "org": self.org,
            "invitees": self.invitees,
            "role": self.role,
            "dry_run": self.dry_run,
        }
        if self.team is not None:
            self.payload["team"] = self.team


# --------------------------------------------------------------------------- #
# Repositories & tags
# --------------------------------------------------------------------------- #


class RepositoryListModel(_PaginatedModel):
    """``GET /v2/namespaces/{namespace}/repositories``."""

    namespace: str = Field(description="User or organization namespace")
    name: str | None = Field(default=None, description="Filter by repository name")
    ordering: str | None = Field(default=None, description="Result ordering")

    @field_validator("ordering")
    @classmethod
    def validate_ordering(cls, value: str | None) -> str | None:
        if value is not None and value not in REPOSITORY_ORDERING:
            raise ValueError(
                f"Invalid ordering {value!r}; valid: {sorted(REPOSITORY_ORDERING)}"
            )
        return value

    def model_post_init(self, _context):
        super().model_post_init(_context)
        assert self.api_parameters is not None
        if self.name:
            self.api_parameters["name"] = self.name
        if self.ordering:
            self.api_parameters["ordering"] = self.ordering


class RepositoryCreateModel(BaseModel):
    """``POST /v2/namespaces/{namespace}/repositories``."""

    namespace: str = Field(description="User or organization namespace")
    name: str = Field(description="Repository name (lowercase)")
    description: str | None = Field(default=None, description="Short description")
    full_description: str | None = Field(
        default=None, description="Long-form (Markdown) description"
    )
    registry: str = Field(default="docker", description="Target registry")
    is_private: bool = Field(default=False, description="Create as private")
    payload: dict | None = Field(description="Request body", default=None)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        import re

        if not re.fullmatch(r"[a-z0-9]+(?:[._-][a-z0-9]+)*", value):
            raise ValueError(
                "Repository names must be lowercase alphanumerics separated by "
                "'.', '_', or '-'"
            )
        return value

    def model_post_init(self, _context):
        self.payload = {
            "name": self.name,
            "namespace": self.namespace,
            "registry": self.registry,
            "is_private": self.is_private,
        }
        if self.description is not None:
            self.payload["description"] = self.description
        if self.full_description is not None:
            self.payload["full_description"] = self.full_description


class RepositoryModel(BaseModel):
    """``GET|HEAD /v2/namespaces/{namespace}/repositories/{repository}``."""

    namespace: str
    repository: str


class TagListModel(_PaginatedModel):
    """``GET|HEAD .../repositories/{repository}/tags``."""

    namespace: str
    repository: str


class TagModel(BaseModel):
    """``GET|HEAD .../repositories/{repository}/tags/{tag}``."""

    namespace: str
    repository: str
    tag: str


class ImmutableTagsPatchModel(BaseModel):
    """``PATCH .../repositories/{repository}/immutabletags``."""

    namespace: str
    repository: str
    enabled: bool = Field(description="Enable or disable tag immutability")
    rules: list[str] | None = Field(
        default=None, description="Tag patterns the immutability applies to"
    )
    payload: dict | None = Field(description="Request body", default=None)

    def model_post_init(self, _context):
        self.payload = {"enabled": self.enabled}
        if self.rules is not None:
            self.payload["rules"] = self.rules


class ImmutableTagsVerifyModel(BaseModel):
    """``POST .../repositories/{repository}/immutabletags/verify``."""

    namespace: str
    repository: str
    rules: list[str] | None = Field(
        default=None, description="Candidate immutability rules to verify"
    )
    tags: list[str] | None = Field(
        default=None, description="Tags to verify against the rules"
    )
    payload: dict | None = Field(description="Request body", default=None)

    @model_validator(mode="after")
    def validate_any_input(self):
        if self.rules is None and self.tags is None:
            raise ValueError("Provide rules and/or tags to verify")
        return self

    def model_post_init(self, _context):
        self.payload = {}
        if self.rules is not None:
            self.payload["rules"] = self.rules
        if self.tags is not None:
            self.payload["tags"] = self.tags


class RepositoryGroupModel(BaseModel):
    """``POST /v2/repositories/{namespace}/{repository}/groups``."""

    namespace: str
    repository: str
    group_id: int | str = Field(description="Team (group) identifier")
    permission: str = Field(description="Permission: read, write, or admin")
    payload: dict | None = Field(description="Request body", default=None)

    @field_validator("permission")
    @classmethod
    def validate_permission(cls, value: str) -> str:
        if value not in REPOSITORY_PERMISSIONS:
            raise ValueError(
                f"Invalid permission {value!r}; valid: {sorted(REPOSITORY_PERMISSIONS)}"
            )
        return value

    def model_post_init(self, _context):
        self.payload = {"group_id": self.group_id, "permission": self.permission}


# --------------------------------------------------------------------------- #
# Groups (teams)
# --------------------------------------------------------------------------- #


class GroupListModel(_PaginatedModel):
    """``GET /v2/orgs/{org}/groups``."""

    org: str
    search: str | None = Field(default=None, description="Search by group name")

    def model_post_init(self, _context):
        super().model_post_init(_context)
        assert self.api_parameters is not None
        if self.search:
            self.api_parameters["search"] = self.search


class GroupCreateModel(BaseModel):
    """``POST /v2/orgs/{org}/groups``."""

    org: str
    name: str = Field(description="Group (team) name")
    description: str | None = None
    payload: dict | None = Field(description="Request body", default=None)

    def model_post_init(self, _context):
        self.payload = {"name": self.name}
        if self.description is not None:
            self.payload["description"] = self.description


class GroupModel(BaseModel):
    """``GET|DELETE /v2/orgs/{org}/groups/{group}``."""

    org: str
    group_name: str


class GroupUpdateModel(BaseModel):
    """``PUT|PATCH /v2/orgs/{org}/groups/{group}``."""

    org: str
    group_name: str
    name: str | None = None
    description: str | None = None
    payload: dict | None = Field(description="Request body", default=None)

    @model_validator(mode="after")
    def validate_any_change(self):
        if self.name is None and self.description is None:
            raise ValueError("Provide name and/or description to update")
        return self

    def model_post_init(self, _context):
        self.payload = {}
        if self.name is not None:
            self.payload["name"] = self.name
        if self.description is not None:
            self.payload["description"] = self.description


class GroupMemberListModel(_PaginatedModel):
    """``GET /v2/orgs/{org}/groups/{group}/members``."""

    org: str
    group_name: str
    search: str | None = Field(default=None, description="Search by username")

    def model_post_init(self, _context):
        super().model_post_init(_context)
        assert self.api_parameters is not None
        if self.search:
            self.api_parameters["search"] = self.search


class GroupMemberAddModel(BaseModel):
    """``POST /v2/orgs/{org}/groups/{group}/members``."""

    org: str
    group_name: str
    member: str = Field(description="Username to add to the group")
    payload: dict | None = Field(description="Request body", default=None)

    def model_post_init(self, _context):
        self.payload = {"member": self.member}


class GroupMemberModel(BaseModel):
    """``DELETE /v2/orgs/{org}/groups/{group}/members/{username}``."""

    org: str
    group_name: str
    username: str


# --------------------------------------------------------------------------- #
# SCIM 2.0
# --------------------------------------------------------------------------- #


class ScimUserListModel(BaseModel):
    """``GET /v2/scim/2.0/Users`` (SCIM-style 1-based pagination)."""

    start_index: int | None = Field(
        default=None, ge=1, description="1-based index of the first result"
    )
    count: int | None = Field(default=None, ge=0, description="Max results to return")
    filter: str | None = Field(
        default=None, description='SCIM filter, e.g. userName eq "jane"'
    )
    sort_by: str | None = Field(default=None, description="Attribute to sort by")
    sort_order: str | None = Field(default=None, description="ascending or descending")
    api_parameters: dict | None = Field(description="API parameters", default=None)

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, value: str | None) -> str | None:
        if value is not None and value not in SCIM_SORT_ORDERS:
            raise ValueError(
                f"Invalid sort order {value!r}; valid: {sorted(SCIM_SORT_ORDERS)}"
            )
        return value

    def model_post_init(self, _context):
        self.api_parameters = {}
        if self.start_index is not None:
            self.api_parameters["startIndex"] = self.start_index
        if self.count is not None:
            self.api_parameters["count"] = self.count
        if self.filter:
            self.api_parameters["filter"] = self.filter
        if self.sort_by:
            self.api_parameters["sortBy"] = self.sort_by
        if self.sort_order:
            self.api_parameters["sortOrder"] = self.sort_order


SCIM_USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"


class ScimUserCreateModel(BaseModel):
    """``POST /v2/scim/2.0/Users``."""

    user_name: str = Field(description="SCIM userName (email address)")
    given_name: str | None = None
    family_name: str | None = None
    email: str | None = Field(
        default=None, description="Primary email (defaults to user_name)"
    )
    active: bool = Field(default=True)
    payload: dict | None = Field(description="Request body", default=None)

    def model_post_init(self, _context):
        self.payload = {
            "schemas": [SCIM_USER_SCHEMA],
            "userName": self.user_name,
            "active": self.active,
        }
        name: dict = {}
        if self.given_name is not None:
            name["givenName"] = self.given_name
        if self.family_name is not None:
            name["familyName"] = self.family_name
        if name:
            self.payload["name"] = name
        email = self.email or self.user_name
        self.payload["emails"] = [{"value": email, "primary": True}]


class ScimUserModel(BaseModel):
    """``GET /v2/scim/2.0/Users/{id}``."""

    user_id: str = Field(description="SCIM user identifier")


class ScimUserReplaceModel(BaseModel):
    """``PUT /v2/scim/2.0/Users/{id}`` — full resource replacement."""

    user_id: str = Field(description="SCIM user identifier")
    user_name: str = Field(description="SCIM userName (email address)")
    given_name: str | None = None
    family_name: str | None = None
    email: str | None = None
    active: bool = Field(default=True)
    payload: dict | None = Field(description="Request body", default=None)

    def model_post_init(self, _context):
        self.payload = {
            "schemas": [SCIM_USER_SCHEMA],
            "id": self.user_id,
            "userName": self.user_name,
            "active": self.active,
        }
        name: dict = {}
        if self.given_name is not None:
            name["givenName"] = self.given_name
        if self.family_name is not None:
            name["familyName"] = self.family_name
        if name:
            self.payload["name"] = name
        email = self.email or self.user_name
        self.payload["emails"] = [{"value": email, "primary": True}]


# --------------------------------------------------------------------------- #
# Registry HTTP API v2
# --------------------------------------------------------------------------- #


class RegistryTagsListModel(BaseModel):
    """``GET /v2/{repo}/tags/list`` (registry-native pagination)."""

    repo: str = Field(description="Image repository, e.g. 'nginx' or 'org/app'")
    n: int | None = Field(default=None, ge=1, description="Max tags to return")
    last: str | None = Field(
        default=None, description="Return tags lexically after this tag"
    )
    api_parameters: dict | None = Field(description="API parameters", default=None)

    def model_post_init(self, _context):
        self.api_parameters = {}
        if self.n is not None:
            self.api_parameters["n"] = self.n
        if self.last:
            self.api_parameters["last"] = self.last


class RegistryReferrersModel(BaseModel):
    """``GET /v2/{repo}/referrers/{digest}`` (OCI 1.1 referrers)."""

    repo: str = Field(description="Image repository")
    digest: str = Field(description="Subject manifest digest (sha256:...)")
    artifact_type: str | None = Field(
        default=None,
        description="Filter referrers by artifactType, sent as 'artifactType'",
    )
    api_parameters: dict | None = Field(description="API parameters", default=None)

    def model_post_init(self, _context):
        self.api_parameters = {}
        if self.artifact_type:
            self.api_parameters["artifactType"] = self.artifact_type

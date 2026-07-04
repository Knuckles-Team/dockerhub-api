"""Pydantic response models for the Docker Hub API client.

CONCEPT:DH-OS.audit.core-wrapper-api-is — core wrapper.

Models are intentionally lenient (``extra="allow"``, optional fields) so they
survive Docker Hub schema evolution: known fields get typed, unknown fields
ride along. Client methods validate response data against these models when
the shape is known and fall back to raw JSON when validation fails.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HubModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class RateLimit(HubModel):
    """Snapshot of the ``X-RateLimit-*`` headers from the latest response."""

    limit: int | None = Field(default=None, description="Request ceiling")
    remaining: int | None = Field(default=None, description="Requests remaining")
    reset: int | None = Field(default=None, description="Window reset (epoch s)")


class Page(HubModel):
    """Standard Docker Hub page envelope (``count``/``next``/``previous``)."""

    count: int | None = None
    next: str | None = None
    previous: str | None = None
    results: list[Any] | None = None


class JwtToken(HubModel):
    """``POST /v2/auth/token`` response."""

    access_token: str | None = None
    token: str | None = None


class LoginResult(HubModel):
    """``POST /v2/users/login`` / ``POST /v2/users/2fa-login`` response."""

    token: str | None = None
    refresh_token: str | None = None
    detail: str | None = None
    login_2fa_token: str | None = None


class AccessToken(HubModel):
    """A personal access token record."""

    uuid: str | None = None
    token_label: str | None = None
    token: str | None = Field(
        default=None, description="Plaintext token — only present on creation"
    )
    scopes: list[str] | None = None
    is_active: bool | None = None
    client_id: str | None = None
    creator_ip: str | None = None
    creator_ua: str | None = None
    created_at: str | None = None
    last_used: str | None = None
    generated_by: str | None = None


class AccessTokenPage(Page):
    active_count: int | None = None
    results: list[AccessToken] | None = None  # type: ignore[assignment]


class OrgAccessToken(HubModel):
    """An organization access token record."""

    id: str | None = None
    uuid: str | None = None
    label: str | None = None
    description: str | None = None
    token: str | None = Field(
        default=None, description="Plaintext token — only present on creation"
    )
    scopes: list[str] | None = None
    resources: list[dict] | None = None
    is_active: bool | None = None
    created_at: str | None = None
    expires_at: str | None = None


class OrgAccessTokenPage(Page):
    results: list[OrgAccessToken] | None = None  # type: ignore[assignment]


class AuditLogEvent(HubModel):
    """One audit-log entry."""

    account: str | None = None
    action: str | None = None
    name: str | None = None
    actor: str | None = None
    actor_ip: str | None = None
    data: dict | None = None
    timestamp: str | None = None


class AuditLogPage(HubModel):
    logs: list[AuditLogEvent] | None = None
    count: int | None = None


class AuditLogActions(HubModel):
    """``GET /v2/auditlogs/{account}/actions`` response."""

    actions: dict | list | None = None


class RestrictedImages(HubModel):
    enabled: bool | None = None
    allow_official_images: bool | None = None
    allow_verified_publishers: bool | None = None


class OrgSettings(HubModel):
    """``GET|PUT /v2/orgs/{name}/settings`` response."""

    restricted_images: RestrictedImages | None = None


class Repository(HubModel):
    """A Docker Hub image repository."""

    name: str | None = None
    namespace: str | None = None
    repository_type: str | None = None
    description: str | None = None
    full_description: str | None = None
    registry: str | None = None
    is_private: bool | None = None
    status: int | str | None = None
    star_count: int | None = None
    pull_count: int | None = None
    last_updated: str | None = None
    date_registered: str | None = None
    affiliation: str | None = None
    media_types: list[str] | None = None


class RepositoryPage(Page):
    results: list[Repository] | None = None  # type: ignore[assignment]


class TagImage(HubModel):
    architecture: str | None = None
    os: str | None = None
    digest: str | None = None
    size: int | None = None
    status: str | None = None
    last_pushed: str | None = None
    last_pulled: str | None = None


class Tag(HubModel):
    """A repository tag."""

    id: int | None = None
    name: str | None = None
    repository: int | str | None = None
    full_size: int | None = None
    digest: str | None = None
    images: list[TagImage] | None = None
    last_updated: str | None = None
    last_updater_username: str | None = None
    tag_status: str | None = None
    tag_last_pulled: str | None = None
    tag_last_pushed: str | None = None
    v2: bool | str | None = None
    content_type: str | None = None
    media_type: str | None = None


class TagPage(Page):
    results: list[Tag] | None = None  # type: ignore[assignment]


class ImmutableTagsSettings(HubModel):
    """``PATCH .../immutabletags`` response."""

    enabled: bool | None = None
    rules: list[str] | None = None


class ImmutableTagsVerification(HubModel):
    """``POST .../immutabletags/verify`` response."""

    enabled: bool | None = None
    rules: list[str] | None = None
    results: list[dict] | None = None
    errors: list[dict] | None = None


class RepositoryGroup(HubModel):
    """``POST /v2/repositories/{ns}/{repo}/groups`` response."""

    group_id: int | str | None = None
    group_name: str | None = None
    permission: str | None = None


class OrgMember(HubModel):
    """An organization member."""

    id: str | None = None
    username: str | None = None
    full_name: str | None = None
    email: str | None = None
    role: str | None = None
    type: str | None = None
    groups: list[str] | None = None
    is_guest: bool | None = None
    last_logged_in_date: str | None = None
    joined_at: str | None = None


class OrgMemberPage(Page):
    results: list[OrgMember] | None = None  # type: ignore[assignment]


class Invite(HubModel):
    """An organization invite."""

    id: str | None = None
    invitee: str | None = None
    inviter: str | None = None
    org: str | None = None
    team: str | None = None
    role: str | None = None
    created_at: str | None = None
    status: str | None = None


class InvitePage(Page):
    data: list[Invite] | None = None
    results: list[Invite] | None = None  # type: ignore[assignment]


class BulkInviteResult(HubModel):
    """``POST /v2/invites/bulk`` response."""

    org: str | None = None
    team: str | None = None
    role: str | None = None
    dry_run: bool | None = None
    invitees: list[dict] | list[str] | None = None
    valid: list[Any] | None = None
    invalid: list[Any] | None = None


class Group(HubModel):
    """An organization group (team)."""

    id: int | str | None = None
    name: str | None = None
    description: str | None = None
    member_count: int | None = None


class GroupPage(Page):
    results: list[Group] | None = None  # type: ignore[assignment]


class ScimName(HubModel):
    givenName: str | None = None
    familyName: str | None = None


class ScimEmail(HubModel):
    value: str | None = None
    primary: bool | None = None


class ScimUser(HubModel):
    """A SCIM 2.0 User resource."""

    schemas: list[str] | None = None
    id: str | None = None
    userName: str | None = None
    name: ScimName | None = None
    emails: list[ScimEmail] | None = None
    active: bool | None = None
    groups: list[dict] | None = None
    meta: dict | None = None


class ScimListResponse(HubModel):
    """SCIM 2.0 list envelope (``ListResponse``)."""

    schemas: list[str] | None = None
    totalResults: int | None = None
    startIndex: int | None = None
    itemsPerPage: int | None = None
    Resources: list[dict] | None = None


class ScimServiceProviderConfig(HubModel):
    schemas: list[str] | None = None
    patch: dict | None = None
    bulk: dict | None = None
    filter: dict | None = None
    changePassword: dict | None = None
    sort: dict | None = None
    etag: dict | None = None
    authenticationSchemes: list[dict] | None = None


class ScimResourceType(HubModel):
    schemas: list[str] | None = None
    id: str | None = None
    name: str | None = None
    endpoint: str | None = None
    schema_uri: str | None = Field(default=None, alias="schema")


class ScimSchema(HubModel):
    id: str | None = None
    name: str | None = None
    description: str | None = None
    attributes: list[dict] | None = None


# --------------------------------------------------------------------------- #
# Registry HTTP API v2
# --------------------------------------------------------------------------- #


class RegistryTagList(HubModel):
    """``GET /v2/{repo}/tags/list`` response."""

    name: str | None = None
    tags: list[str] | None = None


class RegistryDescriptor(HubModel):
    """An OCI content descriptor (config, layer, or child manifest)."""

    mediaType: str | None = None
    digest: str | None = None
    size: int | None = None
    artifactType: str | None = None
    platform: dict | None = None
    annotations: dict | None = None


class RegistryManifest(HubModel):
    """An image manifest, manifest list, or OCI index."""

    schemaVersion: int | None = None
    mediaType: str | None = None
    artifactType: str | None = None
    config: RegistryDescriptor | None = None
    layers: list[RegistryDescriptor] | None = None
    manifests: list[RegistryDescriptor] | None = None
    subject: RegistryDescriptor | None = None
    annotations: dict | None = None


class RegistryPlatform(HubModel):
    """A single platform entry resolved from a manifest list / OCI index."""

    os: str | None = None
    architecture: str | None = None
    variant: str | None = None
    digest: str | None = None
    size: int | None = None
    mediaType: str | None = None


class ImageConfig(HubModel):
    """A container image config blob (the ``application/...image.v1+json``)."""

    architecture: str | None = None
    os: str | None = None
    variant: str | None = None
    created: str | None = None
    config: dict | None = None
    rootfs: dict | None = None
    history: list[dict] | None = None


class ReferrerList(HubModel):
    """``GET /v2/{repo}/referrers/{digest}`` response (an OCI index)."""

    schemaVersion: int | None = None
    mediaType: str | None = None
    manifests: list[RegistryDescriptor] | None = None


# --------------------------------------------------------------------------- #
# Docker Scout
# --------------------------------------------------------------------------- #


class ScoutImageSummary(HubModel):
    """A Docker Scout image-analysis summary (vulnerability roll-up)."""

    digest: str | None = None
    vulnerabilities: dict | list | None = None
    policy: dict | list | None = None
    sbom: dict | None = None


class ScoutVulnerabilities(HubModel):
    """A Docker Scout CVE / vulnerability listing."""

    cves: list[dict] | None = None
    vulnerabilities: list[dict] | None = None
    items: list[dict] | None = None
    count: int | None = None


class ScoutPolicyEvaluation(HubModel):
    """A Docker Scout policy evaluation result."""

    policies: list[dict] | None = None
    results: list[dict] | None = None
    outcome: str | None = None


def validate_lenient(model: type[BaseModel], data: Any) -> Any:
    """Validate ``data`` against ``model``; fall back to the raw data.

    Keeps client results JSON-serializable while still exercising the typed
    models whenever the payload matches the documented shape.
    """
    if data is None:
        return None
    try:
        return model.model_validate(data).model_dump(mode="json", exclude_none=True)
    except Exception:  # pragma: no cover - lenient by design
        return data

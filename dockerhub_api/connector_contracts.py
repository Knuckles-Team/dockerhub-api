"""Tool-use contracts, surface links, data locations and business roles of dockerhub-mcp.

The SDK serves this declaration as the connector's surface ontology and checks it
against the served tools, prompts and skills (SCION-CONNECTOR-CONTROL-R916).
"""

# ruff: noqa: E501
from __future__ import annotations

from scion_sdk.surface_contracts import (
    BusinessRole,
    DataLocation,
    Refusal,
    SurfaceLink,
    ToolStep,
    ToolUseContract,
)

CONTRACTS: tuple[ToolUseContract, ...] = (
    ToolUseContract(
        "provision-release-repository",
        description="Create an image repository for a release and lock its tags",
        steps=(
            ToolStep(
                "dockerhub_get_repositories",
                params=("namespace", "name"),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                    Refusal("not_found", "the named object does not exist"),
                ),
            ),
            ToolStep(
                "dockerhub_check_repository",
                params=("namespace", "repository"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_create_repository",
                params=("namespace", "name"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_update_immutable_tags",
                params=("namespace", "repository", "enabled"),
                result=("result",),
                refusals=(Refusal("not_found", "the named object does not exist"),),
            ),
            ToolStep(
                "dockerhub_verify_immutable_tags",
                params=("namespace", "repository"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_get_repository",
                params=("namespace", "repository"),
                result=("result",),
                refusals=(Refusal("not_found", "the named object does not exist"),),
            ),
        ),
    ),
    ToolUseContract(
        "audit-repository-tags",
        description="List a repository's tags and confirm each one exists",
        steps=(
            ToolStep(
                "dockerhub_get_repository_tags",
                params=("namespace", "repository"),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                    Refusal("not_found", "the named object does not exist"),
                ),
            ),
            ToolStep(
                "dockerhub_get_repository_tag",
                params=("namespace", "repository", "tag"),
                result=("result",),
                refusals=(Refusal("not_found", "the named object does not exist"),),
            ),
            ToolStep(
                "dockerhub_check_repository_tag",
                params=("namespace", "repository", "tag"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_check_repository_tags",
                params=("namespace", "repository"),
                result=("result",),
                refusals=(),
            ),
        ),
    ),
    ToolUseContract(
        "ingest-repository-catalog",
        description="Mirror the repositories of a namespace into the knowledge graph",
        steps=(
            ToolStep(
                "dockerhub_get_repositories",
                params=("namespace",),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                    Refusal("not_found", "the named object does not exist"),
                ),
            ),
            ToolStep(
                "dockerhub_ingest_repositories",
                params=("namespace",),
                result=("result",),
                refusals=(),
            ),
        ),
    ),
    ToolUseContract(
        "grant-team-repository-access",
        description="Give a team a permission on a repository",
        steps=(
            ToolStep(
                "dockerhub_get_groups",
                params=("org",),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                    Refusal("not_found", "the named object does not exist"),
                ),
            ),
            ToolStep(
                "dockerhub_assign_repository_group",
                params=("namespace", "repository", "group_id", "permission"),
                result=("result",),
                refusals=(),
            ),
        ),
    ),
    ToolUseContract(
        "inspect-image",
        description="Resolve a tag to a digest and read the manifest, platforms and config of an image",
        steps=(
            ToolStep(
                "dockerhub_registry_api_version",
                params=(),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                ),
            ),
            ToolStep(
                "dockerhub_registry_list_tags",
                params=("repo",),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_registry_resolve_digest",
                params=("repo", "reference"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_registry_check_manifest",
                params=("repo", "reference"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_registry_get_manifest",
                params=("repo", "reference"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_registry_list_platforms",
                params=("repo", "reference"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_registry_get_config",
                params=("repo", "reference"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_registry_inspect",
                params=("repo", "reference"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_registry_check_blob",
                params=("repo", "digest"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_registry_get_blob",
                params=("repo", "digest"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_registry_list_referrers",
                params=("repo", "digest"),
                result=("result",),
                refusals=(),
            ),
        ),
    ),
    ToolUseContract(
        "publish-image-content",
        description="Push a manifest and its blobs to a repository, or remove them",
        steps=(
            ToolStep(
                "dockerhub_registry_start_upload",
                params=("repo",),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                ),
            ),
            ToolStep(
                "dockerhub_registry_upload_chunk",
                params=("repo", "location", "chunk"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_registry_complete_upload",
                params=("repo", "location", "digest"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_registry_mount_blob",
                params=("repo", "digest", "from_repo"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_registry_put_manifest",
                params=("repo", "reference", "manifest", "media_type"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_registry_delete_manifest",
                params=("repo", "reference"),
                result=("result",),
                refusals=(
                    Refusal(
                        "confirmation_required",
                        "the destructive call omits confirm=true",
                    ),
                ),
            ),
            ToolStep(
                "dockerhub_registry_delete_blob",
                params=("repo", "digest"),
                result=("result",),
                refusals=(
                    Refusal(
                        "confirmation_required",
                        "the destructive call omits confirm=true",
                    ),
                ),
            ),
        ),
    ),
    ToolUseContract(
        "assess-image-vulnerabilities",
        description="Read the vulnerability, SBOM and policy picture of an image and compare two images",
        steps=(
            ToolStep(
                "dockerhub_scout_get_image_summary",
                params=("repo",),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                ),
            ),
            ToolStep(
                "dockerhub_scout_list_vulnerabilities",
                params=("repo",),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_scout_get_cves",
                params=("repo",),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_scout_get_sbom",
                params=("repo",),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_scout_list_policies",
                params=("org",),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_scout_get_policy_evaluation",
                params=("repo",),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_scout_compare",
                params=("repo", "base_ref", "target_ref"),
                result=("result",),
                refusals=(),
            ),
        ),
    ),
    ToolUseContract(
        "review-organization-audit-trail",
        description="Read the audit events of a namespace",
        steps=(
            ToolStep(
                "dockerhub_get_audit_log_actions",
                params=("account",),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                    Refusal("not_found", "the named object does not exist"),
                ),
            ),
            ToolStep(
                "dockerhub_get_audit_logs",
                params=("account",),
                result=("result",),
                refusals=(Refusal("not_found", "the named object does not exist"),),
            ),
        ),
    ),
    ToolUseContract(
        "manage-organization-members",
        description="Invite, list, re-role and remove organization members",
        steps=(
            ToolStep(
                "dockerhub_get_org_members",
                params=("org",),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                    Refusal("not_found", "the named object does not exist"),
                ),
            ),
            ToolStep(
                "dockerhub_export_org_members",
                params=("org",),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_bulk_invite",
                params=("org", "invitees"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_get_org_invites",
                params=("org",),
                result=("result",),
                refusals=(Refusal("not_found", "the named object does not exist"),),
            ),
            ToolStep(
                "dockerhub_resend_invite",
                params=("invite_id",),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_delete_invite",
                params=("invite_id",),
                result=("result",),
                refusals=(
                    Refusal(
                        "confirmation_required",
                        "the destructive call omits confirm=true",
                    ),
                    Refusal("not_found", "the named object does not exist"),
                ),
            ),
            ToolStep(
                "dockerhub_update_org_member",
                params=("org", "username", "role"),
                result=("result",),
                refusals=(Refusal("not_found", "the named object does not exist"),),
            ),
            ToolStep(
                "dockerhub_remove_org_member",
                params=("org", "username"),
                result=("result",),
                refusals=(
                    Refusal(
                        "confirmation_required",
                        "the destructive call omits confirm=true",
                    ),
                    Refusal("not_found", "the named object does not exist"),
                ),
            ),
        ),
    ),
    ToolUseContract(
        "manage-teams",
        description="Create teams, change their membership and delete them",
        steps=(
            ToolStep(
                "dockerhub_get_groups",
                params=("org",),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                    Refusal("not_found", "the named object does not exist"),
                ),
            ),
            ToolStep(
                "dockerhub_get_group",
                params=("org", "group_name"),
                result=("result",),
                refusals=(Refusal("not_found", "the named object does not exist"),),
            ),
            ToolStep(
                "dockerhub_create_group",
                params=("org", "name"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_update_group",
                params=("org", "group_name"),
                result=("result",),
                refusals=(Refusal("not_found", "the named object does not exist"),),
            ),
            ToolStep(
                "dockerhub_patch_group",
                params=("org", "group_name"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_get_group_members",
                params=("org", "group_name"),
                result=("result",),
                refusals=(Refusal("not_found", "the named object does not exist"),),
            ),
            ToolStep(
                "dockerhub_add_group_member",
                params=("org", "group_name", "member"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_remove_group_member",
                params=("org", "group_name", "username"),
                result=("result",),
                refusals=(
                    Refusal(
                        "confirmation_required",
                        "the destructive call omits confirm=true",
                    ),
                    Refusal("not_found", "the named object does not exist"),
                ),
            ),
            ToolStep(
                "dockerhub_delete_group",
                params=("org", "group_name"),
                result=("result",),
                refusals=(
                    Refusal(
                        "confirmation_required",
                        "the destructive call omits confirm=true",
                    ),
                    Refusal("not_found", "the named object does not exist"),
                ),
            ),
        ),
    ),
    ToolUseContract(
        "set-organization-image-policy",
        description="Read and change which image sources the organization may use",
        steps=(
            ToolStep(
                "dockerhub_get_org_settings",
                params=("org",),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                    Refusal("not_found", "the named object does not exist"),
                ),
            ),
            ToolStep(
                "dockerhub_update_org_settings",
                params=("org", "restricted_images_enabled"),
                result=("result",),
                refusals=(Refusal("not_found", "the named object does not exist"),),
            ),
        ),
    ),
    ToolUseContract(
        "manage-organization-access-tokens",
        description="Issue, review, change and revoke organization access tokens",
        steps=(
            ToolStep(
                "dockerhub_get_org_access_tokens",
                params=("org",),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                    Refusal("not_found", "the named object does not exist"),
                ),
            ),
            ToolStep(
                "dockerhub_get_org_access_token",
                params=("org", "token_id"),
                result=("result",),
                refusals=(Refusal("not_found", "the named object does not exist"),),
            ),
            ToolStep(
                "dockerhub_create_org_access_token",
                params=("org", "label"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_update_org_access_token",
                params=("org", "token_id"),
                result=("result",),
                refusals=(Refusal("not_found", "the named object does not exist"),),
            ),
            ToolStep(
                "dockerhub_delete_org_access_token",
                params=("org", "token_id"),
                result=("result",),
                refusals=(
                    Refusal(
                        "confirmation_required",
                        "the destructive call omits confirm=true",
                    ),
                    Refusal("not_found", "the named object does not exist"),
                ),
            ),
        ),
    ),
    ToolUseContract(
        "manage-personal-access-tokens",
        description="Sign in, issue, review, change and revoke personal access tokens",
        steps=(
            ToolStep(
                "dockerhub_login",
                params=("username", "password"),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                ),
            ),
            ToolStep(
                "dockerhub_two_factor_login",
                params=("login_2fa_token", "code"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_create_auth_token",
                params=("identifier", "secret"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_get_access_tokens",
                params=("page", "page_size"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_get_access_token",
                params=("uuid",),
                result=("result",),
                refusals=(Refusal("not_found", "the named object does not exist"),),
            ),
            ToolStep(
                "dockerhub_create_access_token",
                params=("token_label", "scopes"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_update_access_token",
                params=("uuid",),
                result=("result",),
                refusals=(Refusal("not_found", "the named object does not exist"),),
            ),
            ToolStep(
                "dockerhub_delete_access_token",
                params=("uuid",),
                result=("result",),
                refusals=(
                    Refusal(
                        "confirmation_required",
                        "the destructive call omits confirm=true",
                    ),
                    Refusal("not_found", "the named object does not exist"),
                ),
            ),
            ToolStep("hub_admin_whoami", params=(), result=("result",), refusals=()),
            ToolStep(
                "hub_admin_rate_limit", params=(), result=("result",), refusals=()
            ),
        ),
    ),
    ToolUseContract(
        "provision-scim-users",
        description="Read the SCIM schema and create or replace provisioned users",
        steps=(
            ToolStep(
                "dockerhub_get_scim_service_provider_config",
                params=(),
                result=("result",),
                refusals=(
                    Refusal(
                        "access_denied", "the credential lacks access to the system"
                    ),
                ),
            ),
            ToolStep(
                "dockerhub_get_scim_resource_types",
                params=(),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_get_scim_resource_type",
                params=("name",),
                result=("result",),
                refusals=(Refusal("not_found", "the named object does not exist"),),
            ),
            ToolStep(
                "dockerhub_get_scim_schemas", params=(), result=("result",), refusals=()
            ),
            ToolStep(
                "dockerhub_get_scim_schema",
                params=("schema_id",),
                result=("result",),
                refusals=(Refusal("not_found", "the named object does not exist"),),
            ),
            ToolStep(
                "dockerhub_get_scim_users",
                params=("start_index", "count", "filter"),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_get_scim_user",
                params=("user_id",),
                result=("result",),
                refusals=(Refusal("not_found", "the named object does not exist"),),
            ),
            ToolStep(
                "dockerhub_create_scim_user",
                params=("user_name",),
                result=("result",),
                refusals=(),
            ),
            ToolStep(
                "dockerhub_replace_scim_user",
                params=("user_id", "user_name"),
                result=("result",),
                refusals=(),
            ),
        ),
    ),
)

LINKS: tuple[SurfaceLink, ...] = (
    SurfaceLink(
        "provision-release-repository",
        tools=(
            "dockerhub_get_repositories",
            "dockerhub_check_repository",
            "dockerhub_create_repository",
            "dockerhub_update_immutable_tags",
            "dockerhub_verify_immutable_tags",
            "dockerhub_get_repository",
        ),
        prompts=("dockerhub-mcp-operator", "dockerhub-mcp-release-engineer"),
        skills=("dockerhub-api-operations", "dockerhub-repository-management"),
    ),
    SurfaceLink(
        "audit-repository-tags",
        tools=(
            "dockerhub_get_repository_tags",
            "dockerhub_get_repository_tag",
            "dockerhub_check_repository_tag",
            "dockerhub_check_repository_tags",
        ),
        prompts=("dockerhub-mcp-operator", "dockerhub-mcp-release-engineer"),
        skills=("dockerhub-repository-management",),
    ),
    SurfaceLink(
        "ingest-repository-catalog",
        tools=("dockerhub_get_repositories", "dockerhub_ingest_repositories"),
        prompts=("dockerhub-mcp-operator", "dockerhub-mcp-release-engineer"),
        skills=("dockerhub-repository-management",),
    ),
    SurfaceLink(
        "grant-team-repository-access",
        tools=("dockerhub_get_groups", "dockerhub_assign_repository_group"),
        prompts=(
            "dockerhub-mcp-operator",
            "dockerhub-mcp-release-engineer",
            "dockerhub-mcp-organization-administrator",
        ),
        skills=("dockerhub-org-administration", "dockerhub-repository-management"),
    ),
    SurfaceLink(
        "inspect-image",
        tools=(
            "dockerhub_registry_api_version",
            "dockerhub_registry_list_tags",
            "dockerhub_registry_resolve_digest",
            "dockerhub_registry_check_manifest",
            "dockerhub_registry_get_manifest",
            "dockerhub_registry_list_platforms",
            "dockerhub_registry_get_config",
            "dockerhub_registry_inspect",
            "dockerhub_registry_check_blob",
            "dockerhub_registry_get_blob",
            "dockerhub_registry_list_referrers",
        ),
        prompts=(
            "dockerhub-mcp-operator",
            "dockerhub-mcp-release-engineer",
            "dockerhub-mcp-security-analyst",
        ),
        skills=("dockerhub-api-operations", "dockerhub-image-registry-scout"),
    ),
    SurfaceLink(
        "publish-image-content",
        tools=(
            "dockerhub_registry_start_upload",
            "dockerhub_registry_upload_chunk",
            "dockerhub_registry_complete_upload",
            "dockerhub_registry_mount_blob",
            "dockerhub_registry_put_manifest",
            "dockerhub_registry_delete_manifest",
            "dockerhub_registry_delete_blob",
        ),
        prompts=("dockerhub-mcp-operator", "dockerhub-mcp-release-engineer"),
        skills=("dockerhub-image-registry-scout",),
    ),
    SurfaceLink(
        "assess-image-vulnerabilities",
        tools=(
            "dockerhub_scout_get_image_summary",
            "dockerhub_scout_list_vulnerabilities",
            "dockerhub_scout_get_cves",
            "dockerhub_scout_get_sbom",
            "dockerhub_scout_list_policies",
            "dockerhub_scout_get_policy_evaluation",
            "dockerhub_scout_compare",
        ),
        prompts=("dockerhub-mcp-operator", "dockerhub-mcp-security-analyst"),
        skills=("dockerhub-api-operations", "dockerhub-image-registry-scout"),
    ),
    SurfaceLink(
        "review-organization-audit-trail",
        tools=("dockerhub_get_audit_log_actions", "dockerhub_get_audit_logs"),
        prompts=("dockerhub-mcp-operator", "dockerhub-mcp-security-analyst"),
        skills=("dockerhub-org-administration",),
    ),
    SurfaceLink(
        "manage-organization-members",
        tools=(
            "dockerhub_get_org_members",
            "dockerhub_export_org_members",
            "dockerhub_bulk_invite",
            "dockerhub_get_org_invites",
            "dockerhub_resend_invite",
            "dockerhub_delete_invite",
            "dockerhub_update_org_member",
            "dockerhub_remove_org_member",
        ),
        prompts=("dockerhub-mcp-operator", "dockerhub-mcp-organization-administrator"),
        skills=("dockerhub-api-operations", "dockerhub-org-administration"),
    ),
    SurfaceLink(
        "manage-teams",
        tools=(
            "dockerhub_get_groups",
            "dockerhub_get_group",
            "dockerhub_create_group",
            "dockerhub_update_group",
            "dockerhub_patch_group",
            "dockerhub_get_group_members",
            "dockerhub_add_group_member",
            "dockerhub_remove_group_member",
            "dockerhub_delete_group",
        ),
        prompts=("dockerhub-mcp-operator", "dockerhub-mcp-organization-administrator"),
        skills=("dockerhub-org-administration",),
    ),
    SurfaceLink(
        "set-organization-image-policy",
        tools=("dockerhub_get_org_settings", "dockerhub_update_org_settings"),
        prompts=("dockerhub-mcp-operator", "dockerhub-mcp-organization-administrator"),
        skills=("dockerhub-org-administration",),
    ),
    SurfaceLink(
        "manage-organization-access-tokens",
        tools=(
            "dockerhub_get_org_access_tokens",
            "dockerhub_get_org_access_token",
            "dockerhub_create_org_access_token",
            "dockerhub_update_org_access_token",
            "dockerhub_delete_org_access_token",
        ),
        prompts=("dockerhub-mcp-operator", "dockerhub-mcp-organization-administrator"),
        skills=("dockerhub-org-administration",),
    ),
    SurfaceLink(
        "manage-personal-access-tokens",
        tools=(
            "dockerhub_login",
            "dockerhub_two_factor_login",
            "dockerhub_create_auth_token",
            "dockerhub_get_access_tokens",
            "dockerhub_get_access_token",
            "dockerhub_create_access_token",
            "dockerhub_update_access_token",
            "dockerhub_delete_access_token",
            "hub_admin_whoami",
            "hub_admin_rate_limit",
        ),
        prompts=("dockerhub-mcp-operator", "dockerhub-mcp-organization-administrator"),
        skills=("dockerhub-org-administration",),
    ),
    SurfaceLink(
        "provision-scim-users",
        tools=(
            "dockerhub_get_scim_service_provider_config",
            "dockerhub_get_scim_resource_types",
            "dockerhub_get_scim_resource_type",
            "dockerhub_get_scim_schemas",
            "dockerhub_get_scim_schema",
            "dockerhub_get_scim_users",
            "dockerhub_get_scim_user",
            "dockerhub_create_scim_user",
            "dockerhub_replace_scim_user",
        ),
        prompts=("dockerhub-mcp-operator", "dockerhub-mcp-organization-administrator"),
        skills=("dockerhub-org-administration",),
    ),
)

LOCATIONS: tuple[DataLocation, ...] = (
    DataLocation(
        "dockerhub-repositories",
        ("Repository", "ContainerImage"),
        "DOCKERHUB_URL",
        "dockerhub_get_repositories",
        federation_key="name",
    ),
    DataLocation(
        "dockerhub-registry",
        ("ContainerImage",),
        "DOCKER_REGISTRY_URL",
        "dockerhub_registry_list_tags",
        federation_key="repo",
    ),
    DataLocation(
        "dockerhub-scout",
        ("Vulnerability",),
        "DOCKER_SCOUT_URL",
        "dockerhub_scout_list_vulnerabilities",
        federation_key="repo",
    ),
    DataLocation(
        "dockerhub-organization",
        ("Organization", "Team", "AccessToken"),
        "DOCKERHUB_URL",
        "dockerhub_get_org_members",
        federation_key="org",
    ),
    DataLocation(
        "dockerhub-audit-log",
        ("Organization",),
        "DOCKERHUB_URL",
        "dockerhub_get_audit_logs",
        federation_key="account",
    ),
)

ROLES: tuple[BusinessRole, ...] = (
    BusinessRole(
        "release-engineer",
        tasks=(
            "provision-release-repository",
            "audit-repository-tags",
            "ingest-repository-catalog",
            "inspect-image",
            "publish-image-content",
            "grant-team-repository-access",
        ),
    ),
    BusinessRole(
        "organization-administrator",
        tasks=(
            "manage-organization-members",
            "manage-teams",
            "set-organization-image-policy",
            "manage-organization-access-tokens",
            "manage-personal-access-tokens",
            "provision-scim-users",
            "grant-team-repository-access",
        ),
    ),
    BusinessRole(
        "security-analyst",
        tasks=(
            "assess-image-vulnerabilities",
            "inspect-image",
            "review-organization-audit-trail",
        ),
    ),
)

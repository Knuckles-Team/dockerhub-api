---
name: dockerhub-org-administration
skill_type: skill
description: >-
  Administer a Docker Hub organization through the dockerhub-mcp tools: members and invitations, teams, image policy, personal and organization access tokens, SCIM users and the audit trail. Use for access reviews and joiner-mover-leaver work. Not for image content.
license: MIT
tags: [dockerhub, organization, teams, tokens, scim]
metadata:
  author: Knuckles-Team
  version: '1.0.0'
---
# Docker Hub organization administration

Organization data lives under the org namespace. Token values are returned once at creation and are redacted everywhere else.

## Rules

- Export members before any bulk change and use dry_run on bulk invites.
- Removals and deletions need the person's agreement and confirm=true.
- Never print a token or secret value after its creation response.

## Task workflows

### review-organization-audit-trail

Read the audit events of a namespace. Contract steps, in order:

1. `dockerhub_get_audit_log_actions`(account)
2. `dockerhub_get_audit_logs`(account; optional audit_action, name, actor, from_date, to_date, page)

### manage-organization-members

Invite, list, re-role and remove organization members. Contract steps, in order:

1. `dockerhub_get_org_members`(org; optional search, member_type, role, page, page_size)
2. `dockerhub_export_org_members`(org)
3. `dockerhub_bulk_invite`(org, invitees; optional team, role, dry_run)
4. `dockerhub_get_org_invites`(org)
5. `dockerhub_resend_invite`(invite_id)
6. `dockerhub_delete_invite`(invite_id; optional confirm) (destructive: pass confirm=true only after the person agrees)
7. `dockerhub_update_org_member`(org, username, role)
8. `dockerhub_remove_org_member`(org, username; optional confirm) (destructive: pass confirm=true only after the person agrees)

### manage-teams

Create teams, change their membership and delete them. Contract steps, in order:

1. `dockerhub_get_groups`(org; optional search, page, page_size)
2. `dockerhub_get_group`(org, group_name)
3. `dockerhub_create_group`(org, name; optional description)
4. `dockerhub_update_group`(org, group_name; optional name, description)
5. `dockerhub_patch_group`(org, group_name; optional name, description)
6. `dockerhub_get_group_members`(org, group_name; optional search, page, page_size)
7. `dockerhub_add_group_member`(org, group_name, member)
8. `dockerhub_remove_group_member`(org, group_name, username; optional confirm) (destructive: pass confirm=true only after the person agrees)
9. `dockerhub_delete_group`(org, group_name; optional confirm) (destructive: pass confirm=true only after the person agrees)

### set-organization-image-policy

Read and change which image sources the organization may use. Contract steps, in order:

1. `dockerhub_get_org_settings`(org)
2. `dockerhub_update_org_settings`(org, restricted_images_enabled; optional allow_official_images, allow_verified_publishers)

### manage-organization-access-tokens

Issue, review, change and revoke organization access tokens. Contract steps, in order:

1. `dockerhub_get_org_access_tokens`(org; optional page, page_size)
2. `dockerhub_get_org_access_token`(org, token_id)
3. `dockerhub_create_org_access_token`(org, label; optional description, expires_at, scopes, resources)
4. `dockerhub_update_org_access_token`(org, token_id; optional label, description, is_active)
5. `dockerhub_delete_org_access_token`(org, token_id; optional confirm) (destructive: pass confirm=true only after the person agrees)

### manage-personal-access-tokens

Sign in, issue, review, change and revoke personal access tokens. Contract steps, in order:

1. `dockerhub_login`(username, password)
2. `dockerhub_two_factor_login`(login_2fa_token, code)
3. `dockerhub_create_auth_token`(identifier, secret)
4. `dockerhub_get_access_tokens`(; optional page, page_size)
5. `dockerhub_get_access_token`(uuid)
6. `dockerhub_create_access_token`(token_label, scopes)
7. `dockerhub_update_access_token`(uuid; optional token_label, is_active)
8. `dockerhub_delete_access_token`(uuid; optional confirm) (destructive: pass confirm=true only after the person agrees)
9. `hub_admin_whoami`(no arguments)
10. `hub_admin_rate_limit`(no arguments)

### provision-scim-users

Read the SCIM schema and create or replace provisioned users. Contract steps, in order:

1. `dockerhub_get_scim_service_provider_config`(no arguments)
2. `dockerhub_get_scim_resource_types`(no arguments)
3. `dockerhub_get_scim_resource_type`(name)
4. `dockerhub_get_scim_schemas`(no arguments)
5. `dockerhub_get_scim_schema`(schema_id)
6. `dockerhub_get_scim_users`(; optional start_index, count, filter, sort_by, sort_order)
7. `dockerhub_get_scim_user`(user_id)
8. `dockerhub_create_scim_user`(user_name; optional given_name, family_name, email, active)
9. `dockerhub_replace_scim_user`(user_id, user_name; optional given_name, family_name, email, active)

### grant-team-repository-access

Give a team a permission on a repository. Contract steps, in order:

1. `dockerhub_get_groups`(org; optional search, page, page_size)
2. `dockerhub_assign_repository_group`(namespace, repository, group_id, permission)

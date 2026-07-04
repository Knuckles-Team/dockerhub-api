---
name: dockerhub-org-administration
description: >-
  Administer a Docker Hub organization via the dockerhub-api MCP server — manage
  org settings and restricted-images policy, members and invites (`hub_org`),
  teams/groups and their membership (`hub_teams`), personal and organization
  access tokens (`hub_auth`), SCIM user provisioning (`hub_scim`), and audit logs
  (`hub_audit`). Use when the agent must onboard/offboard members, provision teams
  and tokens, enforce image policy, or review the audit trail. Do NOT use for
  repository/tag operations (dockerhub-repository-management) or registry/CVE
  inspection (dockerhub-image-registry-scout).
license: MIT
tags: [dockerhub, organization, teams, tokens, scim, audit, mcp]
metadata:
  author: Genius
  version: '0.1.0'
---
# Docker Hub Organization Administration

Identity, access, and governance for a Docker Hub **organization** — settings,
members, teams, access tokens, SCIM provisioning, and the audit log. Prefer the
domain-typed tools; several actions are destructive and gated.

## When to use
- Read/update org settings (the **restricted images** policy).
- List/invite/remove members; resend or cancel invites.
- Create/inspect teams (groups) and manage their membership.
- Mint, list, or revoke personal (PAT) and organization (OAT) access tokens.
- Provision users via **SCIM 2.0** (list/get/create/update).
- Review the org **audit log** and the available audit actions.

## When NOT to use
- Repositories, tags, immutable tags, repo-team permission grants →
  `dockerhub-repository-management` (`hub_repos assign_group`).
- Registry manifests/blobs or Docker Scout CVEs →
  `dockerhub-image-registry-scout`.
- Destructive writes (member removal, invite/token deletion, org-settings write)
  unless `DOCKERHUB_ALLOW_DESTRUCTIVE=True`.

## Prerequisites & environment
Connect via the `mcp-client` skill against the **`dockerhub-api`** MCP server.

| Variable | Required | Notes |
|----------|----------|-------|
| `DOCKER_HUB_USER` | ✅ | Docker Hub username (org owner/editor for writes) |
| `DOCKER_HUB_TOKEN` | ✅ | PAT or password |
| `DOCKERHUB_URL` | optional | Defaults to `https://hub.docker.com` |
| `DOCKERHUB_ALLOW_DESTRUCTIVE` | optional | Gate for removals/deletes/settings writes |

`MCP_TOOL_MODE` (`condensed`|`verbose`|`both`) selects the condensed surface.

## Tools & actions
| Condensed tool | Actions |
|----------------|---------|
| `hub_org` | `get_settings`, `update_settings`, `list_members`, `export_members`, `update_member`, `remove_member`, `list_invites`, `delete_invite`, `resend_invite`, `bulk_invite` |
| `hub_teams` | `list`, `create`, `get`, `update`, `patch`, `delete`, `list_members`, `add_member`, `remove_member` |
| `hub_auth` | `create_token`, `login`, `two_factor_login`, `list_pats`, `create_pat`, `get_pat`, `update_pat`, `delete_pat`, `list_oats`, `create_oat`, `get_oat`, `update_oat`, `delete_oat` |
| `hub_scim` | `service_provider_config`, `resource_types`, `resource_type`, `schemas`, `schema`, `list_users`, `get_user`, `create_user`, `update_user` |
| `hub_audit` | `logs`, `actions` |

### Key parameters
- `org` — the organization name (required for `hub_org` / `hub_audit` actions).
- `username` / `role` — `update_member`, `add_member` (`owner`/`editor`/`member`).
- `invitees` + `team` + `role` — `bulk_invite` (use `dry_run` to validate).
- `scopes` — PAT/OAT creation (e.g. `repo:read`, `repo:write`).

## Recipes (`params_json`)
List org members ordered by role:
```json
{"org":"mycorp","role":"owner","page_size":50}
```
Enforce restricted images (block non-approved pulls):
```json
{"org":"mycorp","restricted_images_enabled":true,"allow_official_images":true,"allow_verified_publishers":false}
```
Bulk-invite editors to a team (validate first):
```json
{"org":"mycorp","invitees":["a@corp.com","b@corp.com"],"team":"backend","role":"member","dry_run":true}
```
Create a read-only PAT:
```json
{"token_label":"ci-readonly","scopes":["repo:read"]}
```
Review recent audit events:
```json
{"org":"mycorp"}
```

## Gotchas
- `params_json` is a **string** of JSON, not an object.
- `create_pat` / `create_oat` return the **plaintext token exactly once** — it is
  the one secret field allowed through the redactor on creation; store it
  immediately, subsequent reads never expose it.
- `remove_member`, `delete_invite`, `delete_pat`/`delete_oat`, `delete` (team), and
  `update_settings` are **destructive** — they require `DOCKERHUB_ALLOW_DESTRUCTIVE=True`.
- `role` values are `owner` / `editor` / `member`; team membership is separate from
  org membership.
- SCIM writes assume the org has SSO/SCIM provisioning enabled.

## Related
- Repository/tag operations → `dockerhub-repository-management`.
- Registry + Scout inspection → `dockerhub-image-registry-scout`.
- Members and teams surface in the KG as `:Person` / `:Team` / `:Organization`
  nodes federated by the dockerhub ontology.

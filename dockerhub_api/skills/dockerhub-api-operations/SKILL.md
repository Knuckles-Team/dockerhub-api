---
name: dockerhub-api-operations
skill_type: skill
description: >-
  Cross-cutting Docker Hub operator workflow: provision a release repository, inspect and assess an image, and review membership through the dockerhub-mcp tools. Use when a request spans repositories, images and people.
license: MIT
tags: [dockerhub, operations]
metadata:
  author: Knuckles-Team
  version: '1.0.0'
---
# Docker Hub operations

This skill strings the specialised dockerhub skills together for an end-to-end operator request. Start read-only, then change.

## Rules

- Name the namespace and repository in every report.
- Prefer the specialised skills for details of each step.
- Stop and ask before any destructive call.

## Task workflows

### provision-release-repository

Create an image repository for a release and lock its tags. Contract steps, in order:

1. `dockerhub_get_repositories`(namespace; optional name, ordering, page, page_size)
2. `dockerhub_check_repository`(namespace, repository)
3. `dockerhub_create_repository`(namespace, name; optional description, full_description, registry, is_private)
4. `dockerhub_update_immutable_tags`(namespace, repository, enabled; optional rules)
5. `dockerhub_verify_immutable_tags`(namespace, repository; optional rules, tags)
6. `dockerhub_get_repository`(namespace, repository)

### inspect-image

Resolve a tag to a digest and read the manifest, platforms and config of an image. Contract steps, in order:

1. `dockerhub_registry_api_version`(no arguments)
2. `dockerhub_registry_list_tags`(repo; optional n, last)
3. `dockerhub_registry_resolve_digest`(repo, reference)
4. `dockerhub_registry_check_manifest`(repo, reference)
5. `dockerhub_registry_get_manifest`(repo, reference; optional accept)
6. `dockerhub_registry_list_platforms`(repo, reference)
7. `dockerhub_registry_get_config`(repo, reference)
8. `dockerhub_registry_inspect`(repo, reference; optional include_config)
9. `dockerhub_registry_check_blob`(repo, digest)
10. `dockerhub_registry_get_blob`(repo, digest)
11. `dockerhub_registry_list_referrers`(repo, digest; optional artifact_type)

### assess-image-vulnerabilities

Read the vulnerability, SBOM and policy picture of an image and compare two images. Contract steps, in order:

1. `dockerhub_scout_get_image_summary`(repo; optional reference, org)
2. `dockerhub_scout_list_vulnerabilities`(repo; optional reference, org, severity)
3. `dockerhub_scout_get_cves`(repo; optional reference, org, severity)
4. `dockerhub_scout_get_sbom`(repo; optional reference, org, sbom_format)
5. `dockerhub_scout_list_policies`(org)
6. `dockerhub_scout_get_policy_evaluation`(repo; optional reference, org)
7. `dockerhub_scout_compare`(repo, base_ref, target_ref; optional org)

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

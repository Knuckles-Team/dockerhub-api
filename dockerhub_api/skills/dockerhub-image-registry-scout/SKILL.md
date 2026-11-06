---
name: dockerhub-image-registry-scout
skill_type: skill
description: >-
  Inspect OCI images at the registry level, publish or remove manifests and blobs, and read Docker Scout vulnerability, SBOM and policy results through the dockerhub-mcp tools. Use to resolve a tag to a digest, inspect a multi-arch image, or assess an image. Not for repository or member administration.
license: MIT
tags: [dockerhub, registry, oci, scout]
metadata:
  author: Knuckles-Team
  version: '1.0.0'
---
# Docker Hub image registry and Scout

The registry tools talk to the OCI registry with per-repository tokens; the Scout tools talk to the Scout API. Both address images by repo (for example library/nginx) and reference (tag or digest).

## Rules

- Resolve a tag to a digest first and report the digest, never only the tag.
- Registry deletes and manifest pushes change released content; ask first and pass confirm=true only on agreement.
- Read-only unless the person asks to publish or delete.

## Task workflows

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

### publish-image-content

Push a manifest and its blobs to a repository, or remove them. Contract steps, in order:

1. `dockerhub_registry_start_upload`(repo)
2. `dockerhub_registry_upload_chunk`(repo, location, chunk; optional content_range)
3. `dockerhub_registry_complete_upload`(repo, location, digest; optional final_chunk)
4. `dockerhub_registry_mount_blob`(repo, digest, from_repo)
5. `dockerhub_registry_put_manifest`(repo, reference, manifest, media_type)
6. `dockerhub_registry_delete_manifest`(repo, reference; optional confirm) (destructive: pass confirm=true only after the person agrees)
7. `dockerhub_registry_delete_blob`(repo, digest; optional confirm) (destructive: pass confirm=true only after the person agrees)

### assess-image-vulnerabilities

Read the vulnerability, SBOM and policy picture of an image and compare two images. Contract steps, in order:

1. `dockerhub_scout_get_image_summary`(repo; optional reference, org)
2. `dockerhub_scout_list_vulnerabilities`(repo; optional reference, org, severity)
3. `dockerhub_scout_get_cves`(repo; optional reference, org, severity)
4. `dockerhub_scout_get_sbom`(repo; optional reference, org, sbom_format)
5. `dockerhub_scout_list_policies`(org)
6. `dockerhub_scout_get_policy_evaluation`(repo; optional reference, org)
7. `dockerhub_scout_compare`(repo, base_ref, target_ref; optional org)

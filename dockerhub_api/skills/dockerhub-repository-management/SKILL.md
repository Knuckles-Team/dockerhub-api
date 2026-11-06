---
name: dockerhub-repository-management
skill_type: skill
description: >-
  Create and lock Docker Hub release repositories, audit their tags, grant teams access and mirror the catalog into the knowledge graph through the dockerhub-mcp tools. Use when a release needs a repository or a tag must be verified. Not for image content (dockerhub-image-registry-scout) or people and tokens (dockerhub-org-administration).
license: MIT
tags: [dockerhub, repositories, tags]
metadata:
  author: Knuckles-Team
  version: '1.0.0'
---
# Docker Hub repository management

Repositories live in a namespace (a user or organization). Every release repository is created private unless the person says otherwise and gets an immutable-tag rule.

## Rules

- Check the repository exists (dockerhub_check_repository) before creating it.
- Verify an immutable-tag rule with dockerhub_verify_immutable_tags before relying on it.
- Never create a repository without an explicit is_private decision.

## Task workflows

### provision-release-repository

Create an image repository for a release and lock its tags. Contract steps, in order:

1. `dockerhub_get_repositories`(namespace; optional name, ordering, page, page_size)
2. `dockerhub_check_repository`(namespace, repository)
3. `dockerhub_create_repository`(namespace, name; optional description, full_description, registry, is_private)
4. `dockerhub_update_immutable_tags`(namespace, repository, enabled; optional rules)
5. `dockerhub_verify_immutable_tags`(namespace, repository; optional rules, tags)
6. `dockerhub_get_repository`(namespace, repository)

### audit-repository-tags

List a repository's tags and confirm each one exists. Contract steps, in order:

1. `dockerhub_get_repository_tags`(namespace, repository; optional page, page_size)
2. `dockerhub_get_repository_tag`(namespace, repository, tag)
3. `dockerhub_check_repository_tag`(namespace, repository, tag)
4. `dockerhub_check_repository_tags`(namespace, repository)

### ingest-repository-catalog

Mirror the repositories of a namespace into the knowledge graph. Contract steps, in order:

1. `dockerhub_get_repositories`(namespace; optional name, ordering, page, page_size)
2. `dockerhub_ingest_repositories`(namespace; optional name, ordering, page, page_size, include_tags)

### grant-team-repository-access

Give a team a permission on a repository. Contract steps, in order:

1. `dockerhub_get_groups`(org; optional search, page, page_size)
2. `dockerhub_assign_repository_group`(namespace, repository, group_id, permission)


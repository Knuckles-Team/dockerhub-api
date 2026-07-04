---
name: dockerhub-repository-management
description: >-
  Manage Docker Hub image repositories and tags via the dockerhub-api MCP server
  — list/create/inspect repositories, browse tags, configure immutable-tag rules,
  and grant teams repository permissions with the domain-typed `hub_repos` tool.
  Use when the agent must provision an image repo, audit a namespace's
  repositories, inspect a tag's digest/size/platform, or lock tags immutable. Do
  NOT use for low-level registry manifest/blob operations or CVE scanning
  (dockerhub-image-registry-scout), org/team/member administration
  (dockerhub-org-administration), or pushing typed repos into the knowledge graph
  (that is the internal `dockerhub_ingest_repositories` tool).
license: MIT
tags: [dockerhub, repositories, tags, container-registry, mcp]
metadata:
  author: Genius
  version: '0.1.0'
---
# Docker Hub Repository Management

Domain-typed access to Docker Hub **image repositories and tags** under a
namespace (`/v2/namespaces/{ns}/repositories`). Prefer the `hub_repos` tool over
raw HTTP — it carries the namespace/repository conventions and returns
repository- and tag-shaped records.

## When to use
- List / audit the repositories in a namespace (name filter + ordering).
- Create an image repository for a release (allowed by default).
- Inspect one repository or one tag (digest, size, platform, last-pushed).
- Configure or verify **immutable-tag** rules on a repository.
- Grant a team `read`/`write`/`admin` on a repository.

## When NOT to use
- Registry v2 manifest/blob/digest operations or multi-arch inspect → the
  `dockerhub-image-registry-scout` skill (`hub_registry`).
- CVE / SBOM / policy analysis of an image → `dockerhub-image-registry-scout`
  (`hub_scout`).
- Org settings, members, invites, teams CRUD, tokens, SCIM →
  `dockerhub-org-administration`.
- Bulk-loading repositories as typed KG nodes → the internal
  `dockerhub_ingest_repositories` tool (ingestion, not operations).

## Prerequisites & environment
Connect via the `mcp-client` skill against the **`dockerhub-api`** MCP server.

| Variable | Required | Notes |
|----------|----------|-------|
| `DOCKER_HUB_USER` | ✅ | Docker Hub username |
| `DOCKER_HUB_TOKEN` | ✅ | PAT or password |
| `DOCKERHUB_URL` | optional | Defaults to `https://hub.docker.com` |
| `DOCKERHUB_ALLOW_DESTRUCTIVE` | optional | Gate for destructive ops (default `False`) |
| `DOCKERHUB_SSL_VERIFY` | optional | TLS verification toggle |

`MCP_TOOL_MODE` (`condensed`|`verbose`|`both`) selects the condensed surface
(used below) vs. the one-to-one verbose tools.

## Tools & actions
Prefer the **condensed** tool; it takes `action` + a `params_json` **JSON string**
whose keys are passed straight to the client method.

| Condensed tool | Actions |
|----------------|---------|
| `hub_repos` | `list`, `create`, `get`, `check`, `list_tags`, `check_tags`, `get_tag`, `check_tag`, `set_immutable_tags`, `verify_immutable_tags`, `assign_group` |

### Key parameters
- `namespace` — required for every action (the account/org owning the repo).
- `repository` — required to target one repo (`get`, `list_tags`, `get_tag`, …).
- `name` / `ordering` / `page` / `page_size` — `list` filters and pagination.
- `enabled` + `rules` — `set_immutable_tags` payload.
- `group_id` + `permission` — `assign_group` (`read`/`write`/`admin`).

## Recipes (`params_json`)
List a namespace's repositories, newest first:
```json
{"namespace":"mycorp","ordering":"-last_updated","page_size":25}
```
Create a private repository:
```json
{"namespace":"mycorp","name":"api-gateway","is_private":true,"description":"Edge API gateway"}
```
Inspect one tag's digest / platform:
```json
{"namespace":"mycorp","repository":"api-gateway","tag":"v1.4.2"}
```
Lock semver tags immutable:
```json
{"namespace":"mycorp","repository":"api-gateway","enabled":true,"rules":["v*"]}
```
Grant a team write access:
```json
{"namespace":"mycorp","repository":"api-gateway","group_id":42,"permission":"write"}
```

## Gotchas
- `params_json` is a **string** of JSON, not an object — serialize it.
- Every action needs an explicit `namespace`; there is no implicit "current user".
- `create` is intentionally **not** destructive-gated (it is the release
  provisioning path); deletes and org-settings writes live elsewhere and require
  `DOCKERHUB_ALLOW_DESTRUCTIVE=True`.
- Tag records nest per-architecture image entries under `images[]` (each with its
  own `digest`/`architecture`/`size`); the top-level `digest` is the manifest-list
  digest for multi-arch tags.
- Prefer a `name` filter + a sane `page_size`; unbounded namespace listings are slow.

## Related
- Registry-level manifests/blobs and Scout CVE intelligence →
  `dockerhub-image-registry-scout`.
- Org/team/member/token/SCIM administration → `dockerhub-org-administration`.
- The internal `dockerhub_ingest_repositories` tool pulls these same repositories
  into the knowledge graph as typed `:Repository` / `:ContainerImage` nodes.

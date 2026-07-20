# Dockerhub Image Registry Scout

Inspect container images at the OCI registry level and analyze their security posture via the dockerhub-api MCP server — resolve manifests/digests, list multi-arch platforms, read image configs and OCI referrers with `hub_registry`, and pull Docker Scout CVE/SBOM/policy intelligence with `hub_scout`. Use when the agent must resolve a tag to a digest, inspect a multi-arch image, diff two images, or get the vulnerability roll-up for an image. Do NOT use for repository/tag CRUD or immutable tags (dockerhub-repository-management), or for org/team/token administration (dockerhub-org-administration).

# Docker Hub Image Registry & Scout

Low-level **Registry v2** image operations (`hub_registry`, against
`registry-1.docker.io`) plus **Docker Scout** security intelligence (`hub_scout`).
These target different hosts and auth models than the management API — Registry
uses per-repository scoped tokens; Scout uses the Scout API.

## When to use
- Resolve a tag → content digest, or list the platforms in a manifest list / OCI index.
- Read an image manifest, config blob, or OCI referrers (SBOM/attestation links).
- `inspect` a multi-arch image in one call (manifest + resolved platforms).
- Pull a Docker Scout **vulnerability summary**, CVE list, SBOM, or policy evaluation.
- Compare two images (`hub_scout` `compare`) for a base-image bump decision.

## When NOT to use
- List/create repositories, browse tags, immutable tags, team perms →
  `dockerhub-repository-management` (`hub_repos`).
- Org settings, members, invites, teams, access tokens, SCIM →
  `dockerhub-org-administration`.
- Destructive registry writes (`delete_manifest`, `delete_blob`, uploads) unless
  `DOCKERHUB_ALLOW_DESTRUCTIVE=True` — prefer read/inspect actions.

## Prerequisites & environment
Connect via the `mcp-client` skill against the **`dockerhub-api`** MCP server.

| Variable | Required | Notes |
|----------|----------|-------|
| `DOCKER_HUB_USER` | ✅ | Docker Hub username |
| `DOCKER_HUB_TOKEN` | ✅ | PAT or password (exchanged for a registry scope token) |
| `DOCKER_REGISTRY_URL` | optional | Defaults to `[configured-endpoint]` |
| `DOCKER_SCOUT_URL` | optional | Defaults to `[configured-endpoint]` |
| `DOCKERHUB_ALLOW_DESTRUCTIVE` | optional | Gate for registry deletes/uploads |

`MCP_TOOL_MODE` (`condensed`|`verbose`|`both`) selects the condensed surface.

## Tools & actions
| Condensed tool | Actions |
|----------------|---------|
| `hub_registry` | `api_version`, `list_tags`, `get_manifest`, `check_manifest`, `resolve_digest`, `list_platforms`, `get_config`, `inspect`, `get_blob`, `check_blob`, `list_referrers`, `delete_manifest`, `delete_blob`, `start_upload`, `upload_chunk`, `complete_upload`, `mount_blob`, `put_manifest` |
| `hub_scout` | `summary`, `cves`, `vulnerabilities`, `sbom`, `compare`, `policies`, `policy_evaluation` |

### Key parameters
- `repository` — namespaced repo path, e.g. `library/nginx` (official images live
  under `library/`).
- `reference` — a tag (`1.27`) or a digest (`sha256:...`) for manifest/config actions.
- `digest` — content digest for `get_blob` / `list_referrers`.
- Scout actions take `repository` + `reference`/`digest` identifying the image.

## Recipes (`params_json`)
Resolve a tag to its digest:
```json
{"repository":"library/nginx","reference":"1.27"}
```
Inspect a multi-arch image (manifest + platforms):
```json
{"repository":"library/nginx","reference":"1.27"}
```
List the platforms in a manifest list:
```json
{"repository":"library/nginx","reference":"1.27"}
```
Docker Scout vulnerability summary for an image:
```json
{"repository":"mycorp/api-gateway","reference":"v1.4.2"}
```
Compare two images for a base bump:
```json
{"repository":"mycorp/api-gateway","reference":"v1.4.2","to":"v1.5.0"}
```

## Gotchas
- `params_json` is a **string** of JSON, not an object.
- Docker Official Images are under the `library/` namespace (`library/nginx`, not
  `nginx`).
- Registry auth is a **per-repository scope token** minted from your Hub
  credentials — a token that reads repo A cannot read repo B; the client handles
  the exchange per call.
- Multi-arch tags return a **manifest list / OCI index**; use `list_platforms` or
  `inspect` to resolve the per-arch child digests before `get_config`.
- Scout actions require a **Scout-enabled** account/organization; expect an
  empty/`error` envelope otherwise.
- `delete_*` and upload actions are destructive-gated behind
  `DOCKERHUB_ALLOW_DESTRUCTIVE`.

## Related
- Repository/tag CRUD and immutable tags → `dockerhub-repository-management`.
- Org/team/token administration → `dockerhub-org-administration`.
- Ingested `:ContainerImage` nodes (digest/architecture/size) come from the
  `dockerhub_ingest_repositories` tool with `include_tags`.

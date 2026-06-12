# Dockerhub Api
## CLI or API | MCP | Agent

![PyPI - Version](https://img.shields.io/pypi/v/dockerhub-api)
![MCP Server](https://badge.mcpx.dev?type=server 'MCP Server')
![PyPI - Downloads](https://img.shields.io/pypi/dd/dockerhub-api)
![GitHub Repo stars](https://img.shields.io/github/stars/Knuckles-Team/dockerhub-api)
![PyPI - License](https://img.shields.io/pypi/l/dockerhub-api)
![GitHub last commit (by committer)](https://img.shields.io/github/last-commit/Knuckles-Team/dockerhub-api)
![GitHub issues](https://img.shields.io/github/issues/Knuckles-Team/dockerhub-api)
![GitHub top language](https://img.shields.io/github/languages/top/Knuckles-Team/dockerhub-api)
![GitHub repo size](https://img.shields.io/github/repo-size/Knuckles-Team/dockerhub-api)
![PyPI - Wheel](https://img.shields.io/pypi/wheel/dockerhub-api)
![PyPI - Implementation](https://img.shields.io/pypi/implementation/dockerhub-api)

*Version: 0.1.0*

> **Documentation** — Installation, deployment, usage across the API, CLI, and MCP
> interfaces, the integrated A2A agent server, and guidance on the backing
> Docker Hub platform are maintained in [docs/](docs/index.md).

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Installation](#installation)
- [Usage](#usage)
  - [Python API / CLI](#python-api--cli)
  - [MCP](#mcp)
  - [Agent (A2A)](#agent-a2a)
- [Environment Variables](#environment-variables)
- [Deployment](#deployment)
- [Safety Model](#safety-model)
- [Concepts](#concepts)
- [License](#license)

---

## Overview

**Dockerhub Api** is a production-grade Agent and Model Context Protocol (MCP) server
that wraps the official **Docker Hub API v2** (`https://hub.docker.com`): repositories
and tags, immutable tags, personal and organization access tokens, organization
members/settings/invites, teams, audit logs, and SCIM 2.0 provisioning — plus the
**Registry HTTP API v2** (`registry-1.docker.io`: manifests, blobs, digests,
multi-arch inspection, OCI referrers, and gated push/delete) and **Docker Scout**
(`api.scout.docker.com`: CVE/SBOM/policy intelligence).

---

## Key Features

- **Consolidated Action-Routed MCP Tools:** Nine togglable tool modules
  (`hub_auth`, `hub_repos`, `hub_org`, `hub_teams`, `hub_audit`, `hub_scim`,
  `hub_admin`, `hub_registry`, `hub_scout`) minimize token overhead in LLM contexts.
- **Three API surfaces, one package:** the Hub *management* API, the *Registry v2*
  image API (its own host + per-repository scoped-token auth), and *Docker Scout*
  — each with the same uniform envelope, redaction, and gating.
- **JWT Auth Lifecycle:** Short-lived bearer minted from `POST /v2/auth/token`
  (password, PAT `dckr_pat_*`, or org access token), cached and refreshed before
  expiry, with one transparent re-mint on 401.
- **Rate-Limit Telemetry:** `X-RateLimit-*` headers surfaced in every result;
  HTTP 429 retried with bounded `Retry-After` backoff.
- **Safety by Default:** Deletes and org-settings writes are gated behind
  `DOCKERHUB_ALLOW_DESTRUCTIVE` (default `False`); secrets are redacted from tool
  results (plaintext tokens appear exactly once — on creation). Repository creation
  stays enabled: it is the primary release-provisioning use case.
- **Integrated Graph Agent:** Built-in Pydantic AI agent (`dockerhub-agent`) with
  A2A and AG-UI web interfaces.
- **Native Telemetry & Tracing:** Out-of-the-box OpenTelemetry exports and Langfuse
  tracing via agent-utilities.

---

## Installation

```bash
pip install dockerhub-api            # API client only
pip install "dockerhub-api[mcp]"     # + MCP server
pip install "dockerhub-api[agent]"   # + A2A agent server
pip install "dockerhub-api[all]"     # everything
```

| Extra | Adds |
|---|---|
| `mcp` | FastMCP server (`dockerhub-mcp`) via `agent-utilities[mcp]` |
| `agent` | Pydantic-AI A2A agent (`dockerhub-agent`) + Logfire via `agent-utilities[agent,logfire]` |
| `all` | `mcp` + `agent` |
| `test` | pytest toolchain for development |

Or pull the published image:

```bash
docker pull knucklessg1/dockerhub-api:latest
```

---

## Usage

### Python API / CLI

```python
from dockerhub_api.auth import get_client

api = get_client()   # reads DOCKERHUB_URL / DOCKER_HUB_USER / DOCKER_HUB_TOKEN

repos = api.get_repositories(namespace="acme", ordering="-last_updated")
api.create_repository(namespace="acme", name="release-images", is_private=True)
tags = api.get_repository_tags(namespace="acme", repository="release-images")
print(api.rate_limit)   # latest X-RateLimit-* snapshot
```

Every client method returns a uniform envelope:
`{"status_code": int, "data": ..., "rate_limit": {"limit", "remaining", "reset"}}`.

### MCP

#### Available MCP Tools

| Tool Module | Toggle Env Var | Enabled by Default | Description & Nested Actions |
|---|---|---|---|
| `hub_auth` | `AUTHTOOL` | True | Token lifecycle: `create_token`, `login` (deprecated), `two_factor_login`, `list_pats`, `create_pat`, `get_pat`, `update_pat`, `delete_pat`, `list_oats`, `create_oat`, `get_oat`, `update_oat`, `delete_oat` |
| `hub_repos` | `REPOSTOOL` | True | Repositories & tags: `list`, `create`, `get`, `check`, `list_tags`, `check_tags`, `get_tag`, `check_tag`, `set_immutable_tags`, `verify_immutable_tags`, `assign_group` |
| `hub_org` | `ORGTOOL` | True | Org admin: `get_settings`, `update_settings`, `list_members`, `export_members`, `update_member`, `remove_member`, `list_invites`, `delete_invite`, `resend_invite`, `bulk_invite` |
| `hub_teams` | `TEAMSTOOL` | True | Teams: `list`, `create`, `get`, `update`, `patch`, `delete`, `list_members`, `add_member`, `remove_member` |
| `hub_audit` | `AUDITTOOL` | True | Audit trail: `logs`, `actions` |
| `hub_scim` | `SCIMTOOL` | True | SCIM 2.0: `service_provider_config`, `resource_types`, `resource_type`, `schemas`, `schema`, `list_users`, `get_user`, `create_user`, `update_user` |
| `hub_admin` | `ADMINTOOL` | True | Diagnostics: `rate_limit`, `whoami` (local JWT introspection) |
| `hub_registry` | `REGISTRYTOOL` | True | Registry v2 (`registry-1.docker.io`): `api_version`, `list_tags`, `get_manifest`, `check_manifest`, `resolve_digest`, `list_platforms`, `get_config`, `inspect`, `get_blob`, `check_blob`, `list_referrers`, `delete_manifest`†, `delete_blob`†, `start_upload`†, `upload_chunk`†, `complete_upload`†, `mount_blob`†, `put_manifest`† |
| `hub_scout` | `SCOUTTOOL` | True | Docker Scout (`api.scout.docker.com`): `summary`, `cves`, `vulnerabilities`, `sbom`, `compare`, `policies`, `policy_evaluation` |

† Gated by `DOCKERHUB_ALLOW_DESTRUCTIVE` (push and delete are destructive).

#### Registry v2 vs. the Hub management API

`hub_registry` targets a **different host and auth model** than the other tools.
The Hub management API (`hub.docker.com`) uses one JWT from `/v2/auth/token`; the
Registry v2 API (`registry-1.docker.io`) authorizes each call with a
**per-repository, per-action** bearer obtained from a token service via a
`401 WWW-Authenticate` challenge. Both reuse the same `DOCKER_HUB_USER` /
`DOCKER_HUB_TOKEN` credentials (anonymous works for public pulls). Single-segment
repository names (e.g. `nginx`) are normalized to their official `library/` path.

`_catalog` (registry-wide repository listing) is intentionally **not** implemented:
Docker Hub does not issue the registry-scoped token it requires. The chunked push
buffers each chunk in memory — it is intended for manifests, config, and
attestation blobs, not as a replacement for `docker push` of large layers.

```python
from dockerhub_api.auth import get_registry_client, get_scout_client

reg = get_registry_client()
print(reg.inspect("nginx", "latest")["data"]["platforms"])      # multi-arch list
digest = reg.resolve_digest("nginx", "latest")["data"]["digest"]
print(reg.list_referrers("nginx", digest)["data"])              # SBOM/attestations

scout = get_scout_client()
print(scout.get_cves("myorg/app", reference="v1")["data"])      # CVE listing
```

Run the server:

```bash
export DOCKER_HUB_USER=youruser
export DOCKER_HUB_TOKEN=dckr_pat_xxx
dockerhub-mcp --transport streamable-http --host 0.0.0.0 --port 8000
```

### Agent (A2A)

```bash
dockerhub-agent --mcp-url http://localhost:8000/mcp --web
```

---

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `DOCKERHUB_URL` | `https://hub.docker.com` | Docker Hub API base URL |
| `DOCKER_HUB_USER` | — | Account identifier (official hub-tool name, primary) |
| `DOCKER_HUB_TOKEN` | — | Password, PAT `dckr_pat_*`, or org access token (primary) |
| `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` | — | Legacy fallback aliases for the two above |
| `DOCKERHUB_JWT` | — | Optional pre-minted bearer (overrides credential exchange) |
| `DOCKERHUB_SSL_VERIFY` | `True` | TLS certificate verification |
| `DOCKERHUB_ALLOW_DESTRUCTIVE` | `False` | Enable deletes and org-settings writes |
| `AUTHTOOL` … `ADMINTOOL` | `True` | Per-module MCP tool toggles (see table above) |
| `HOST` / `PORT` / `TRANSPORT` | `0.0.0.0` / `8000` / `stdio` | MCP server bind & transport (`stdio`, `streamable-http`, `sse`) |
| `AUTH_TYPE` | `none` | MCP server auth mode (Docker image) |
| `MCP_URL` | — | MCP endpoint the A2A agent connects to |
| `ENABLE_OTEL` | `True` | OpenTelemetry / Langfuse export via agent-utilities |
| `EUNOMIA_TYPE` / `EUNOMIA_POLICY_FILE` / `EUNOMIA_REMOTE_URL` | `none` / `mcp_policies.json` / — | Eunomia access-governance middleware |
| `FASTMCP_LOG_LEVEL` / `NO_COLOR` | — | FastMCP logging controls |

A complete annotated template lives in [.env.example](.env.example).

---

## Deployment

Docker Compose definitions ship in [docker/](docker/):

```bash
cp .env.example .env       # fill in DOCKER_HUB_USER / DOCKER_HUB_TOKEN
docker compose -f docker/mcp.compose.yml up -d     # MCP server only
docker compose -f docker/agent.compose.yml up -d   # MCP server + A2A agent (port 9018)
```

Both services expose `/health` endpoints; see
[docs/deployment.md](docs/deployment.md) for transports, Caddy ingress, and
Technitium DNS guidance.

---

<!-- BEGIN GENERATED: additional-deployment-options -->
### Additional Deployment Options

`dockerhub-api` can also run as a **local container** (Docker / Podman / `uv`) or be
consumed from a **remote deployment**. The
[Deployment guide](https://knuckles-team.github.io/dockerhub-api/deployment/) has full, copy-paste
`mcp_config.json` for all four transports — **stdio**, **streamable-http**,
**local container / uv**, and **remote URL**:

- **Local container / uv** — launch the server from `mcp_config.json` via `uvx`,
  `docker run`, or `podman run`, or point at a local streamable-http container by `url`.
- **Remote URL** — connect to a server deployed behind Caddy at
  `http://dockerhub-mcp.arpa/mcp` using the `"url"` key.
<!-- END GENERATED: additional-deployment-options -->

## Safety Model

| Operation class | Default | Override |
|---|---|---|
| Reads (repos, tags, members, logs, SCIM) | allowed | — |
| Repository create / immutable-tag config / invites / role updates | allowed | — |
| Deletes (PATs, OATs, groups, members, invites) | **blocked** | `DOCKERHUB_ALLOW_DESTRUCTIVE=True` |
| Org-settings writes (`PUT /v2/orgs/{org}/settings`) | **blocked** | `DOCKERHUB_ALLOW_DESTRUCTIVE=True` |

---

## Concepts

The concept registry (`CONCEPT:HUB-1.x`) is documented in
[docs/concepts.md](docs/concepts.md).

## License

MIT — see [LICENSE](LICENSE).

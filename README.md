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

*Version: 1.0.0*

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

```bash
# MCP server only (recommended for tool hosting — slim deps)
uv pip install "dockerhub-api[mcp]"

# Full agent runtime (Pydantic AI + epistemic-graph engine)
uv pip install "dockerhub-api[agent]"

# Everything (development)
uv pip install "dockerhub-api[all]"      # or: python -m pip install "dockerhub-api[all]"
```

### Container images (`:mcp` vs `:agent`)

One multi-stage `docker/Dockerfile` builds two right-sized images, selected by `--target`:

| Image tag | Build target | Contents | Entrypoint |
|-----------|--------------|----------|------------|
| `knucklessg1/dockerhub-api:mcp` | `--target mcp` | `dockerhub-api[mcp]` — **slim**, no engine/`pydantic-ai`/`dspy`/`llama-index`/`tree-sitter` | `dockerhub-mcp` |
| `knucklessg1/dockerhub-api:latest` | `--target agent` (default) | `dockerhub-api[agent]` — **full** agent runtime + epistemic-graph engine | `dockerhub-agent` |

```bash
docker build --target mcp   -t knucklessg1/dockerhub-api:mcp    docker/   # slim MCP server
docker build --target agent -t knucklessg1/dockerhub-api:latest docker/   # full agent
```

`docker/mcp.compose.yml` runs the slim `:mcp` server; `docker/agent.compose.yml` runs the
agent (`:latest`) with a co-located `:mcp` sidecar.

### Knowledge-graph database (`epistemic-graph`)

The **full agent** (`[agent]` / `:latest`) embeds the **epistemic-graph** engine (pulled in
transitively via `agent-utilities[agent]`). For production — or to share one knowledge graph
across multiple agents — run **epistemic-graph as its own database container** and point the
agent at it instead of embedding it. Deployment recipes (single-node + Raft HA), connection
config, and the full database architecture (with diagrams) are documented in the
[epistemic-graph deployment guide](https://knuckles-team.github.io/epistemic-graph/deployment/).
The slim `[mcp]` server does **not** require the database.

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

_Auto-generated — do not edit (synced by the `mcp-readme-table` pre-commit hook)._

<!-- MCP-TOOLS-TABLE:START -->

#### Condensed action-routed tools (default — `MCP_TOOL_MODE=condensed`)

| MCP Tool | Toggle Env Var | Description |
|----------|----------------|-------------|
| `hub_admin` | `ADMINTOOL` | Client diagnostics: 'rate_limit' returns the latest |
| `hub_audit` | `AUDITTOOL` | Read a Docker Hub account's audit trail: 'logs' lists events |
| `hub_auth` | `AUTHTOOL` | Manage Docker Hub authentication, personal access tokens (PATs), |
| `hub_org` | `ORGTOOL` | Manage a Docker Hub organization: settings (restricted images), |
| `hub_registry` | `REGISTRYTOOL` | Docker Registry v2 image operations (``registry-1.docker.io``): |
| `hub_repos` | `REPOSTOOL` | Manage Docker Hub repositories: list/create/inspect repositories, |
| `hub_scim` | `SCIMTOOL` | Docker Hub SCIM 2.0: service discovery (ServiceProviderConfig, |
| `hub_scout` | `SCOUTTOOL` | Docker Scout image intelligence (``api.scout.docker.com``): |
| `hub_teams` | `TEAMSTOOL` | Manage Docker Hub organization groups (teams) and their members. |

#### Verbose 1:1 API-mapped tools (`MCP_TOOL_MODE=verbose` or `both`)

<details>
<summary>54 per-operation tools — one per public API method (click to expand)</summary>

| MCP Tool | Toggle Env Var | Description |
|----------|----------------|-------------|
| `dockerhub_add_group_member` | `GROUPSTOOL` | Add a username to a group. |
| `dockerhub_assign_repository_group` | `REPOSITORIESTOOL` | Grant a team (group) ``read``/``write``/``admin`` on a repository. |
| `dockerhub_bulk_invite` | `ORGSTOOL` | Invite many users/emails at once (``POST /v2/invites/bulk``). |
| `dockerhub_check_repository` | `REPOSITORIESTOOL` | HEAD existence check for a repository. |
| `dockerhub_check_repository_tag` | `REPOSITORIESTOOL` | HEAD existence check for one tag. |
| `dockerhub_check_repository_tags` | `REPOSITORIESTOOL` | HEAD check: does the repository have any tags? |
| `dockerhub_create_access_token` | `ACCESS_TOKENSTOOL` | Create a personal access token. |
| `dockerhub_create_auth_token` | `AUTHTOOL` | Mint a short-lived JWT bearer from an identifier + secret. |
| `dockerhub_create_group` | `GROUPSTOOL` | Create a group (team) in an organization. |
| `dockerhub_create_org_access_token` | `ORG_ACCESS_TOKENSTOOL` | Create an organization access token. |
| `dockerhub_create_repository` | `REPOSITORIESTOOL` | Create an image repository in a namespace. |
| `dockerhub_create_scim_user` | `SCIMTOOL` | Provision a SCIM user. |
| `dockerhub_delete_access_token` | `ACCESS_TOKENSTOOL` | Delete a personal access token. Destructive — gated. |
| `dockerhub_delete_group` | `GROUPSTOOL` | Delete a group. Destructive — gated. |
| `dockerhub_delete_invite` | `ORGSTOOL` | Cancel an invite. Destructive — gated. |
| `dockerhub_delete_org_access_token` | `ORG_ACCESS_TOKENSTOOL` | Delete an organization access token. Destructive — gated. |
| `dockerhub_export_org_members` | `ORGSTOOL` | Export the member list as CSV (``GET /members/export``). |
| `dockerhub_get_access_token` | `ACCESS_TOKENSTOOL` | Get one personal access token by UUID. |
| `dockerhub_get_access_tokens` | `ACCESS_TOKENSTOOL` | List the personal access tokens of the authenticated user. |
| `dockerhub_get_audit_log_actions` | `AUDIT_LOGSTOOL` | List the audit-log action names available for a namespace. |
| `dockerhub_get_audit_logs` | `AUDIT_LOGSTOOL` | List audit-log events for a namespace. |
| `dockerhub_get_group` | `GROUPSTOOL` | Get one group. |
| `dockerhub_get_group_members` | `GROUPSTOOL` | List a group's members. |
| `dockerhub_get_groups` | `GROUPSTOOL` | List an organization's groups (teams). |
| `dockerhub_get_org_access_token` | `ORG_ACCESS_TOKENSTOOL` | Get one organization access token by id. |
| `dockerhub_get_org_access_tokens` | `ORG_ACCESS_TOKENSTOOL` | List an organization's access tokens. |
| `dockerhub_get_org_invites` | `ORGSTOOL` | List an organization's pending invites. |
| `dockerhub_get_org_members` | `ORGSTOOL` | List organization members (filter by search/type/role; paginated). |
| `dockerhub_get_org_settings` | `ORGSTOOL` | Get an organization's settings (restricted images policy). |
| `dockerhub_get_repositories` | `REPOSITORIESTOOL` | List a namespace's repositories (name filter + ordering enum). |
| `dockerhub_get_repository` | `REPOSITORIESTOOL` | Get one repository. |
| `dockerhub_get_repository_tag` | `REPOSITORIESTOOL` | Get one tag. |
| `dockerhub_get_repository_tags` | `REPOSITORIESTOOL` | List a repository's tags (paginated). |
| `dockerhub_get_scim_resource_type` | `SCIMTOOL` | Get one SCIM ResourceType by name. |
| `dockerhub_get_scim_resource_types` | `SCIMTOOL` | List the SCIM ResourceTypes. |
| `dockerhub_get_scim_schema` | `SCIMTOOL` | Get one SCIM Schema by id (URN). |
| `dockerhub_get_scim_schemas` | `SCIMTOOL` | List the SCIM Schemas. |
| `dockerhub_get_scim_service_provider_config` | `SCIMTOOL` | Get the SCIM ServiceProviderConfig. |
| `dockerhub_get_scim_user` | `SCIMTOOL` | Get one SCIM user by id. |
| `dockerhub_get_scim_users` | `SCIMTOOL` | List SCIM users (``startIndex``/``count``/``filter``/``sortBy``/``sortOrder``). |
| `dockerhub_login` | `AUTHTOOL` | Authenticate via the legacy login endpoint. |
| `dockerhub_patch_group` | `GROUPSTOOL` | Partially update a group (``PATCH``). |
| `dockerhub_remove_group_member` | `GROUPSTOOL` | Remove a username from a group. Destructive — gated. |
| `dockerhub_remove_org_member` | `ORGSTOOL` | Remove a member from the organization. Destructive — gated. |
| `dockerhub_replace_scim_user` | `SCIMTOOL` | Replace a SCIM user resource (``PUT``). |
| `dockerhub_resend_invite` | `ORGSTOOL` | Resend an invite (``PATCH /v2/invites/{id}/resend``). |
| `dockerhub_two_factor_login` | `AUTHTOOL` | Complete a 2FA login with the TOTP code (``POST /v2/users/2fa-login``). |
| `dockerhub_update_access_token` | `ACCESS_TOKENSTOOL` | Patch a personal access token's label and/or active state. |
| `dockerhub_update_group` | `GROUPSTOOL` | Replace a group's details (``PUT``). |
| `dockerhub_update_immutable_tags` | `REPOSITORIESTOOL` | Patch a repository's immutable-tags settings. |
| `dockerhub_update_org_access_token` | `ORG_ACCESS_TOKENSTOOL` | Patch an organization access token. |
| `dockerhub_update_org_member` | `ORGSTOOL` | Set a member's org role (``owner``, ``editor``, or ``member``). |
| `dockerhub_update_org_settings` | `ORGSTOOL` | Replace an organization's settings. Destructive — gated. |
| `dockerhub_verify_immutable_tags` | `REPOSITORIESTOOL` | Verify immutable-tag rules without applying them. |

</details>

_9 action-routed tool(s) (default) · 54 verbose 1:1 tool(s). Each is enabled unless its `<DOMAIN>TOOL` toggle is set false; `MCP_TOOL_MODE` selects the surface (`condensed` default · `verbose` 1:1 · `both`). Auto-generated — do not edit._
<!-- MCP-TOOLS-TABLE:END -->

### MCP Configuration Examples

<!-- MCP-CONFIG-EXAMPLES:START -->

> **Install the slim `[mcp]` extra.** All examples install `dockerhub-api[mcp]` — the
> MCP-server extra that pulls only the FastMCP / FastAPI tooling (`agent-utilities[mcp]`).
> It deliberately **excludes** the heavy agent runtime (`pydantic-ai`, the epistemic-graph
> engine, `dspy`, `llama-index`), so `uvx` / container installs are far smaller. Use the
> full `[agent]` extra only when you need the integrated Pydantic AI agent.

#### stdio Transport (local IDEs — Cursor, Claude Desktop, VS Code)

```json
{
  "mcpServers": {
    "dockerhub-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "dockerhub-api[mcp]",
        "dockerhub-mcp"
      ],
      "env": {
        "MCP_TOOL_MODE": "condensed",
        "ADMINTOOL": "True",
        "AUDITTOOL": "True",
        "AUTHTOOL": "True",
        "DOCKERHUB_ALLOW_DESTRUCTIVE": "False",
        "DOCKERHUB_JWT": "",
        "DOCKERHUB_TOKEN": "dckr_pat_your_personal_access_token",
        "DOCKERHUB_URL": "https://hub.docker.com",
        "DOCKERHUB_USERNAME": "your_dockerhub_username",
        "DOCKER_HUB_TOKEN": "",
        "DOCKER_HUB_USER": "",
        "DOCKER_REGISTRY_AUTH_URL": "https://auth.docker.io/token",
        "DOCKER_REGISTRY_URL": "https://registry-1.docker.io",
        "DOCKER_SCOUT_URL": "https://api.scout.docker.com",
        "ORGTOOL": "True",
        "REGISTRYTOOL": "True",
        "REPOSTOOL": "True",
        "SCIMTOOL": "True",
        "SCOUTTOOL": "True",
        "TEAMSTOOL": "True"
      }
    }
  }
}
```

#### Streamable-HTTP Transport (networked / production)

```json
{
  "mcpServers": {
    "dockerhub-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "dockerhub-api[mcp]",
        "dockerhub-mcp",
        "--transport",
        "streamable-http",
        "--port",
        "8000"
      ],
      "env": {
        "TRANSPORT": "streamable-http",
        "HOST": "0.0.0.0",
        "PORT": "8000",
        "MCP_TOOL_MODE": "condensed",
        "ADMINTOOL": "True",
        "AUDITTOOL": "True",
        "AUTHTOOL": "True",
        "DOCKERHUB_ALLOW_DESTRUCTIVE": "False",
        "DOCKERHUB_JWT": "",
        "DOCKERHUB_TOKEN": "dckr_pat_your_personal_access_token",
        "DOCKERHUB_URL": "https://hub.docker.com",
        "DOCKERHUB_USERNAME": "your_dockerhub_username",
        "DOCKER_HUB_TOKEN": "",
        "DOCKER_HUB_USER": "",
        "DOCKER_REGISTRY_AUTH_URL": "https://auth.docker.io/token",
        "DOCKER_REGISTRY_URL": "https://registry-1.docker.io",
        "DOCKER_SCOUT_URL": "https://api.scout.docker.com",
        "ORGTOOL": "True",
        "REGISTRYTOOL": "True",
        "REPOSTOOL": "True",
        "SCIMTOOL": "True",
        "SCOUTTOOL": "True",
        "TEAMSTOOL": "True"
      }
    }
  }
}
```

Alternatively, connect to a pre-deployed Streamable-HTTP instance by `url`:

```json
{
  "mcpServers": {
    "dockerhub-mcp": {
      "url": "http://localhost:8000/dockerhub-mcp/mcp"
    }
  }
}
```

Deploying the Streamable-HTTP server via Docker:

```bash
docker run -d \
  --name dockerhub-mcp-mcp \
  -p 8000:8000 \
  -e TRANSPORT=streamable-http \
  -e HOST=0.0.0.0 \
  -e PORT=8000 \
  -e MCP_TOOL_MODE=condensed \
  -e ADMINTOOL=True \
  -e AUDITTOOL=True \
  -e AUTHTOOL=True \
  -e DOCKERHUB_ALLOW_DESTRUCTIVE=False \
  -e DOCKERHUB_JWT="" \
  -e DOCKERHUB_TOKEN=dckr_pat_your_personal_access_token \
  -e DOCKERHUB_URL=https://hub.docker.com \
  -e DOCKERHUB_USERNAME=your_dockerhub_username \
  -e DOCKER_HUB_TOKEN="" \
  -e DOCKER_HUB_USER="" \
  -e DOCKER_REGISTRY_AUTH_URL=https://auth.docker.io/token \
  -e DOCKER_REGISTRY_URL=https://registry-1.docker.io \
  -e DOCKER_SCOUT_URL=https://api.scout.docker.com \
  -e ORGTOOL=True \
  -e REGISTRYTOOL=True \
  -e REPOSTOOL=True \
  -e SCIMTOOL=True \
  -e SCOUTTOOL=True \
  -e TEAMSTOOL=True \
  knucklessg1/dockerhub-api:mcp
```

_Auto-generated from the code-read env surface (`MCP_TOOL_MODE` + package vars) — do not edit._
<!-- MCP-CONFIG-EXAMPLES:END -->

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


<!-- BEGIN agent-os-genesis-deploy (generated; do not edit between markers) -->

## Deploy with `agent-os-genesis`

This package can be provisioned for you — skill-guided — by the **`agent-os-genesis`**
universal skill (its *single-package deploy mode*): it picks your install method, seeds
secrets to OpenBao/Vault (or `.env`), trusts your enterprise CA, registers the MCP
server, and verifies it — the same machinery that stands up the whole Agent OS, narrowed
to just this package. Ask your agent to **"deploy `dockerhub-api` with agent-os-genesis"**.

| Install mode | Command |
|------|---------|
| Bare-metal, prod (PyPI) | `uvx dockerhub-mcp` · or `uv tool install dockerhub-api` |
| Bare-metal, dev (editable) | `uv pip install -e ".[all]"` · or `pip install -e ".[all]"` |
| Container, prod | deploy `knucklessg1/dockerhub-api:latest` via docker-compose / swarm / podman / podman-compose / kubernetes |
| Container, dev (editable) | deploy `docker/compose.dev.yml` (source-mounted at `/src`; edits live on restart) |

Secrets are read-existing + seeded via `vault_sync` — you are only prompted for what's missing.

<!-- END agent-os-genesis-deploy -->

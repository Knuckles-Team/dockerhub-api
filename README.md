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

*Version: 1.0.1*

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
| `agent` | Pydantic-AI A2A agent (`dockerhub-agent`) + Logfire via `agent-utilities[agent-runtime,logfire]` |
| `all` | `mcp` + `agent` |
| `test` | pytest toolchain for development |

```bash
# Connector-focused MCP server (includes the shared graph engine)
uv pip install "dockerhub-api[mcp]"

# Agent runtime (adds model orchestration to the shared graph engine)
uv pip install "dockerhub-api[agent]"

# Everything (development)
uv pip install "dockerhub-api[all]"      # or: python -m pip install "dockerhub-api[all]"
```

### Container images (`:mcp` vs `:agent`)

One multi-stage `docker/Dockerfile` builds two right-sized images, selected by `--target`:

| Image tag | Build target | Contents | Entrypoint |
|-----------|--------------|----------|------------|
| `example/dockerhub-api:mcp` | `--target mcp` | `dockerhub-api[mcp]` — **connector-focused**, includes `epistemic-graph[full]`; no model-orchestration stack | `dockerhub-mcp` |
| `example/dockerhub-api@sha256:<digest>` | `--target agent` (default) | `dockerhub-api[agent]` — **agent runtime**, model orchestration + `epistemic-graph[full]` | `dockerhub-agent` |

```bash
docker build --target mcp   -t example/dockerhub-api:mcp    docker/   # connector-focused MCP server
docker build --target agent -t example/dockerhub-api:agent-local docker/   # agent runtime
```

`docker/mcp.compose.yml` runs the connector-focused `:mcp` server; `docker/agent.compose.yml` runs the
agent (`immutable agent digest`) with a co-located `:mcp` sidecar.

### Knowledge-graph database (`epistemic-graph`)

Both `[mcp]` and `[agent]` carry the **epistemic-graph** engine through the required
Agent Utilities core dependency (`epistemic-graph[full]`). The `[mcp]` extra keeps
the server connector-focused; `[agent]` additionally enables model orchestration. Local
deployments can use the bundled engine. For production or shared state, run
**epistemic-graph as a dedicated database service** and configure the runtime to use it.
Deployment recipes (single-node + Raft HA), connection configuration, and architecture
diagrams are documented in the
[epistemic-graph deployment guide](https://knuckles-team.github.io/epistemic-graph/deployment/).

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
| `dockerhub_ingest_repositories` | `KGTOOL` | Natively ingest repositories into the epistemic-graph as typed :Repository/:ContainerImage nodes. |
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

> **Install the connector-focused `[mcp]` extra.** Examples use `dockerhub-api[mcp]` to add
> FastMCP / FastAPI through `agent-utilities[mcp]`; the required Agent Utilities core
> still carries `epistemic-graph[full]`. The `[agent-runtime]` extra additionally
> enables model orchestration.

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
        "MCP_TOOL_MODE": "intent",
        "ADMINTOOL": "True",
        "AUDITTOOL": "True",
        "AUTHTOOL": "True",
        "DOCKERHUB_ALLOW_DESTRUCTIVE": "False",
        "DOCKERHUB_TLS_PROFILE": "system",
        "DOCKERHUB_TOKEN": "dckr_pat_your_personal_access_token",
        "DOCKERHUB_URL": "https://hub.docker.com",
        "DOCKERHUB_USERNAME": "your_dockerhub_username",
        "DOCKER_REGISTRY_AUTH_URL": "https://auth.docker.io/token",
        "DOCKER_REGISTRY_URL": "https://registry-1.docker.io",
        "DOCKER_SCOUT_URL": "https://api.scout.docker.com",
        "KGTOOL": "True",
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

Runtime references require an alias-aware launcher such as GraphOS. Other
launchers must omit those entries and inject the resolved values through their
own runtime secret boundary.

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
        "HOST": "127.0.0.1",
        "PORT": "8000",
        "MCP_TOOL_MODE": "intent",
        "ADMINTOOL": "True",
        "AUDITTOOL": "True",
        "AUTHTOOL": "True",
        "DOCKERHUB_ALLOW_DESTRUCTIVE": "False",
        "DOCKERHUB_TLS_PROFILE": "system",
        "DOCKERHUB_TOKEN": "dckr_pat_your_personal_access_token",
        "DOCKERHUB_URL": "https://hub.docker.com",
        "DOCKERHUB_USERNAME": "your_dockerhub_username",
        "DOCKER_REGISTRY_AUTH_URL": "https://auth.docker.io/token",
        "DOCKER_REGISTRY_URL": "https://registry-1.docker.io",
        "DOCKER_SCOUT_URL": "https://api.scout.docker.com",
        "KGTOOL": "True",
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

Run a reviewed container image as a least-privilege stdio child (no
listener or published port):

```bash
docker run -i --rm \
  --read-only \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  --pids-limit=256 \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m \
  -e TRANSPORT=stdio \
  -e MCP_TOOL_MODE=intent \
  -e ADMINTOOL=True \
  -e AUDITTOOL=True \
  -e AUTHTOOL=True \
  -e DOCKERHUB_ALLOW_DESTRUCTIVE=False \
  -e DOCKERHUB_TLS_PROFILE=system \
  -e DOCKERHUB_TOKEN=dckr_pat_your_personal_access_token \
  -e DOCKERHUB_URL=https://hub.docker.com \
  -e DOCKERHUB_USERNAME=your_dockerhub_username \
  -e DOCKER_REGISTRY_AUTH_URL=https://auth.docker.io/token \
  -e DOCKER_REGISTRY_URL=https://registry-1.docker.io \
  -e DOCKER_SCOUT_URL=https://api.scout.docker.com \
  -e KGTOOL=True \
  -e ORGTOOL=True \
  -e REGISTRYTOOL=True \
  -e REPOSTOOL=True \
  -e SCIMTOOL=True \
  -e SCOUTTOOL=True \
  -e TEAMSTOOL=True \
  registry.example.invalid/dockerhub-api@sha256:<digest> dockerhub-mcp
```

For containerized network HTTP, supply an authenticated TLS ingress (or
direct server TLS), exact `MCP_ALLOWED_HOSTS`, and an exact trusted-proxy
CIDR policy through the operator-owned deployment profile. The generator
does not emit an unauthenticated non-loopback listener.

_Auto-generated from the code-read env surface (`MCP_TOOL_MODE` + package vars) — do not edit._
<!-- MCP-CONFIG-EXAMPLES:END -->

<!-- BEGIN GENERATED: additional-deployment-options -->
### Additional Deployment Options

`dockerhub-api` can run as a local stdio process or container, or behind a remote
network boundary. The
[Deployment guide](https://knuckles-team.github.io/dockerhub-api/deployment/) carries
the detailed transport contract.

- **Local container** — launch a reviewed immutable image as a least-privilege
  stdio child with no listener or published port.
- **Remote URL** — connect through an operator-supplied authenticated HTTPS
  ingress. Keep its URL, outbound identity references, trust profile, and exact
  `MCP_ALLOWED_HOSTS` in `AgentConfig`.
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

The concept registry (`CONCEPT:DH-OS.governance.hub-x`) is documented in
[docs/concepts.md](docs/concepts.md).

## License

MIT — see [LICENSE](LICENSE).


<!-- BEGIN agent-utilities-deployment (generated; do not edit between markers) -->

## Deploy with `agent-utilities-deployment`

Provision this package with the consolidated **`agent-utilities-deployment`**
workflow. It selects an installed-package, editable-source, or immutable-container
path; records only runtime secret and TLS-profile references in `AgentConfig`; and
runs doctor, registration, policy, observability, and rollback gates. Ask your agent
to **"deploy `dockerhub-api` with agent-utilities-deployment"**.

| Install mode | Command |
|------|---------|
| Installed package | `uv tool install "dockerhub-api[mcp]"`, then run `dockerhub-mcp` |
| Editable source | `uv pip install -e ".[agent]"`, then run `dockerhub-mcp` |
| Immutable container | deploy `registry.example.invalid/dockerhub-api@sha256:<digest>` through the operator-selected orchestrator |

The repository embeds no deployment profile, credential value, certificate path, or
environment-specific endpoint. Supply those at runtime through `AgentConfig` and the
configured secret provider.

<!-- END agent-utilities-deployment -->

<!-- GOVERNED-CAPABILITY:START -->
## Governed capability contract

This package ships a compact canonical skill surface with specialist procedures
kept as referenced workflows. The current MCP tools, skill metadata,
`connector_manifest.yml`, ontology, mappings, shapes, fixtures, migrations,
tool-schema fingerprints, and certification metadata form one versioned
capability contract. Validate them together; do not rely on stale tool names or
historical per-task skill wrappers.

Runtime endpoints, credentials, certificate trust, tenant identity, retention,
and observability policy are deployment inputs and are never packaged values.
See [Configuration, trust, and privacy](docs/configuration.md) before enabling a
network transport, connector ingestion, GraphOS delegation, or trace export.
<!-- GOVERNED-CAPABILITY:END -->

## Environment Variables

<!-- ENV-VARS-TABLE:START -->

#### Package environment variables

| Variable | Example | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` |  |
| `PORT` | `8000` |  |
| `TRANSPORT` | `stdio` | options: stdio, streamable-http, sse |
| `FASTMCP_LOG_LEVEL` | `ERROR` |  |
| `NO_COLOR` | `1` |  |
| `TERM` | `dumb` | forced to "dumb" by the server to disable ANSI/color output |
| `ENABLE_OTEL` | `True` |  |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:8080/api/public/otel` |  |
| `OTEL_EXPORTER_OTLP_PUBLIC_KEY` | secret-injected |  |
| `OTEL_EXPORTER_OTLP_SECRET_KEY` | secret-injected |  |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `http/protobuf` |  |
| `EUNOMIA_TYPE` | `none` | options: none, embedded, remote |
| `EUNOMIA_POLICY_FILE` | `mcp_policies.json` |  |
| `EUNOMIA_REMOTE_URL` | `http://eunomia-server:8000` |  |
| `DOCKER_HUB_USER` | — | Official hub-tool credential names (primary): |
| `DOCKER_HUB_TOKEN` | secret-injected |  |
| `DOCKERHUB_URL` | `https://hub.docker.com` | Fallback aliases: DOCKERHUB_USERNAME / DOCKERHUB_TOKEN / DOCKERHUB_JWT |
| `DOCKERHUB_USERNAME` | `your_dockerhub_username` |  |
| `DOCKERHUB_TOKEN` | secret-injected | password, PAT, or org access token |
| `DOCKERHUB_JWT` | — | optional pre-minted bearer (overrides the above) |
| `DOCKERHUB_TLS_PROFILE` | `system` | Named outbound TLS policy from AgentConfig. Use a reference for runtime-only trust material; peer and hostname verification remain mandatory. |
| `DOCKERHUB_TLS_PROFILE_REF` | — |  |
| `DOCKER_REGISTRY_URL` | `https://registry-1.docker.io` |  |
| `DOCKER_REGISTRY_AUTH_URL` | `https://auth.docker.io/token` | token-service realm; auto-discovered from the 401 challenge |
| `DOCKER_SCOUT_URL` | `https://api.scout.docker.com` |  |
| `DOCKERHUB_ALLOW_DESTRUCTIVE` | `False` |  |
| `AUTHTOOL` | `True` |  |
| `REPOSTOOL` | `True` |  |
| `ORGTOOL` | `True` |  |
| `TEAMSTOOL` | `True` |  |
| `AUDITTOOL` | `True` |  |
| `SCIMTOOL` | `True` |  |
| `ADMINTOOL` | `True` |  |
| `REGISTRYTOOL` | `True` |  |
| `SCOUTTOOL` | `True` |  |
| `KGTOOL` | `True` |  |

#### Inherited agent-utilities variables (apply to every connector)

| Variable | Example | Description |
|----------|---------|-------------|
| `MCP_TOOL_MODE` | `intent` | Tool surface: `intent` \| `condensed` \| `verbose` \| `both` |
| `MCP_ENABLED_TOOLS` | — | Comma-separated tool allow-list |
| `MCP_DISABLED_TOOLS` | — | Comma-separated tool deny-list |
| `MCP_ENABLED_TAGS` | — | Comma-separated tag allow-list |
| `MCP_DISABLED_TAGS` | — | Comma-separated tag deny-list |
| `MCP_CLIENT_AUTH` | — | Outbound MCP child auth: `oidc-client-credentials` \| `basic` \| `none` |
| `OIDC_CLIENT_ID` | — | OIDC client id (service-account auth) |
| `OIDC_CLIENT_SECRET_REF` | `secret://identity/oidc-client-secret` | Runtime secret reference for the OIDC service account |
| `MCP_BASIC_AUTH_USERNAME` | — | HTTP Basic username (`MCP_CLIENT_AUTH=basic`) |
| `MCP_BASIC_AUTH_PASSWORD_REF` | `secret://identity/mcp-basic-password` | Runtime secret reference for HTTP Basic auth (`MCP_CLIENT_AUTH=basic`) |
| `DEBUG` | `False` | Verbose logging |
| `PYTHONUNBUFFERED` | `1` | Unbuffered stdout (recommended in containers) |
| `MCP_URL` | `http://localhost:8000/mcp` | URL of the MCP server the agent connects to |
| `PROVIDER` | `openai` | LLM provider for the agent |
| `MODEL_ID` | `gpt-4o` | Model id for the agent |
| `ENABLE_WEB_UI` | `True` | Serve the AG-UI web interface |

_36 package + 16 inherited variable(s). Auto-generated from `.env.example` + the shared agent-utilities set — do not edit._
<!-- ENV-VARS-TABLE:END -->

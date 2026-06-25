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

*Version: 0.5.0*

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

_9 action-routed tools (default `MCP_TOOL_MODE=condensed`). Each is enabled unless its toggle is set false; set `MCP_TOOL_MODE=verbose` (or `both`) for the 1:1 per-operation surface. Auto-generated — do not edit._
<!-- MCP-TOOLS-TABLE:END -->

#### MCP Configuration Examples

> **Install the slim `[mcp]` extra.** All examples below install
> `dockerhub-api[mcp]` — the MCP-server extra that pulls only the FastMCP /
> FastAPI tooling (`agent-utilities[mcp]`). It deliberately **excludes** the heavy
> agent runtime (the epistemic-graph engine, `pydantic-ai`, `dspy`, `llama-index`,
> `tree-sitter`), so `uvx`/container installs are dramatically smaller and faster.
> Use the full `[agent]` extra only when you need the integrated Pydantic AI agent
> (see [Installation](#installation)).

Configure your IDE's `mcp.json` to launch the MCP server via `uvx`:

```json
{
  "mcpServers": {
    "dockerhub-api": {
      "command": "uvx",
      "args": [
        "--from",
        "dockerhub-api[mcp]",
        "dockerhub-mcp"
      ],
      "env": {
        "DOCKER_HUB_USER": "your_dockerhub_user_here",
        "DOCKER_HUB_TOKEN": "your_dockerhub_token_here"
      }
    }
  }
}
```

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

<!-- ENV-VARS-TABLE:START -->

#### Package environment variables

| Variable | Example | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` |  |
| `PORT` | `8000` |  |
| `TRANSPORT` | `stdio` | options: stdio, streamable-http, sse |
| `FASTMCP_LOG_LEVEL` | `ERROR` |  |
| `NO_COLOR` | `1` |  |
| `ENABLE_OTEL` | `True` |  |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:8080/api/public/otel` |  |
| `OTEL_EXPORTER_OTLP_PUBLIC_KEY` | `pk-...` |  |
| `OTEL_EXPORTER_OTLP_SECRET_KEY` | `sk-...` |  |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `http/protobuf` |  |
| `EUNOMIA_TYPE` | `none` | options: none, embedded, remote |
| `EUNOMIA_POLICY_FILE` | `mcp_policies.json` |  |
| `EUNOMIA_REMOTE_URL` | `http://eunomia-server:8000` |  |
| `DOCKER_HUB_USER` | — | Official hub-tool credential names (primary): |
| `DOCKER_HUB_TOKEN` | — |  |
| `DOCKERHUB_URL` | `https://hub.docker.com` | Fallback aliases: DOCKERHUB_USERNAME / DOCKERHUB_TOKEN / DOCKERHUB_JWT |
| `DOCKERHUB_USERNAME` | `your_dockerhub_username` |  |
| `DOCKERHUB_TOKEN` | `dckr_pat_your_personal_access_token` | password, PAT, or org access token |
| `DOCKERHUB_JWT` | — | optional pre-minted bearer (overrides the above) |
| `DOCKERHUB_SSL_VERIFY` | `True` |  |
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

#### Inherited agent-utilities variables (apply to every connector)

| Variable | Example | Description |
|----------|---------|-------------|
| `MCP_TOOL_MODE` | `condensed` | Tool surface: `condensed` | `verbose` | `both` |
| `MCP_ENABLED_TOOLS` | — | Comma-separated tool allow-list |
| `MCP_DISABLED_TOOLS` | — | Comma-separated tool deny-list |
| `MCP_ENABLED_TAGS` | — | Comma-separated tag allow-list |
| `MCP_DISABLED_TAGS` | — | Comma-separated tag deny-list |
| `MCP_CLIENT_AUTH` | — | Outbound MCP auth (`oidc-client-credentials` for fleet calls) |
| `OIDC_CLIENT_ID` | — | OIDC client id (service-account auth) |
| `OIDC_CLIENT_SECRET` | — | OIDC client secret (service-account auth) |
| `DEBUG` | `False` | Verbose logging |
| `PYTHONUNBUFFERED` | `1` | Unbuffered stdout (recommended in containers) |
| `MCP_URL` | `http://localhost:8000/mcp` | URL of the MCP server the agent connects to |
| `PROVIDER` | `openai` | LLM provider for the agent |
| `MODEL_ID` | `gpt-4o` | Model id for the agent |
| `ENABLE_WEB_UI` | `True` | Serve the AG-UI web interface |

_33 package + 14 inherited variable(s). Auto-generated from `.env.example` + the shared agent-utilities set — do not edit._
<!-- ENV-VARS-TABLE:END -->


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

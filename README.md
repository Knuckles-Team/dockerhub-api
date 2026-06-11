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

## Overview

**Dockerhub Api** is a production-grade Agent and Model Context Protocol (MCP) server
that wraps the official **Docker Hub API v2** (`https://hub.docker.com`): repositories
and tags, immutable tags, personal and organization access tokens, organization
members/settings/invites, teams, audit logs, and SCIM 2.0 provisioning.

---

## Key Features

- **Consolidated Action-Routed MCP Tools:** Seven togglable tool modules
  (`hub_auth`, `hub_repos`, `hub_org`, `hub_teams`, `hub_audit`, `hub_scim`,
  `hub_admin`) minimize token overhead in LLM contexts.
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

## CLI or API

```python
from dockerhub_api.auth import get_client

api = get_client()   # reads DOCKERHUB_URL / DOCKERHUB_USERNAME / DOCKERHUB_TOKEN

repos = api.get_repositories(namespace="acme", ordering="-last_updated")
api.create_repository(namespace="acme", name="release-images", is_private=True)
tags = api.get_repository_tags(namespace="acme", repository="release-images")
print(api.rate_limit)   # latest X-RateLimit-* snapshot
```

Every client method returns a uniform envelope:
`{"status_code": int, "data": ..., "rate_limit": {"limit", "remaining", "reset"}}`.

---

## MCP

### Available MCP Tools

| Tool Module | Toggle Env Var | Enabled by Default | Description & Nested Actions |
|---|---|---|---|
| `hub_auth` | `AUTHTOOL` | True | Token lifecycle: `create_token`, `login` (deprecated), `two_factor_login`, `list_pats`, `create_pat`, `get_pat`, `update_pat`, `delete_pat`, `list_oats`, `create_oat`, `get_oat`, `update_oat`, `delete_oat` |
| `hub_repos` | `REPOSTOOL` | True | Repositories & tags: `list`, `create`, `get`, `check`, `list_tags`, `check_tags`, `get_tag`, `check_tag`, `set_immutable_tags`, `verify_immutable_tags`, `assign_group` |
| `hub_org` | `ORGTOOL` | True | Org admin: `get_settings`, `update_settings`, `list_members`, `export_members`, `update_member`, `remove_member`, `list_invites`, `delete_invite`, `resend_invite`, `bulk_invite` |
| `hub_teams` | `TEAMSTOOL` | True | Teams: `list`, `create`, `get`, `update`, `patch`, `delete`, `list_members`, `add_member`, `remove_member` |
| `hub_audit` | `AUDITTOOL` | True | Audit trail: `logs`, `actions` |
| `hub_scim` | `SCIMTOOL` | True | SCIM 2.0: `service_provider_config`, `resource_types`, `resource_type`, `schemas`, `schema`, `list_users`, `get_user`, `create_user`, `update_user` |
| `hub_admin` | `ADMINTOOL` | True | Diagnostics: `rate_limit`, `whoami` (local JWT introspection) |

Run the server:

```bash
pip install "dockerhub-api[mcp]"
export DOCKERHUB_USERNAME=youruser
export DOCKERHUB_TOKEN=dckr_pat_xxx
dockerhub-mcp --transport streamable-http --host 0.0.0.0 --port 8000
```

---

## Agent (A2A)

```bash
pip install "dockerhub-api[agent]"
dockerhub-agent --mcp-url http://localhost:8000/mcp --web
```

See [docs/deployment.md](docs/deployment.md) for Docker Compose deployments of
both servers.

---

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

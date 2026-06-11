# dockerhub-api

Docker Hub **API + MCP Server + A2A Agent** for the agent-utilities ecosystem — a
typed, action-routed connector for the official Docker Hub API v2
(`https://hub.docker.com`).

!!! info "Official documentation"
    This site is the canonical reference for `dockerhub-api`, maintained alongside
    every release.

[![PyPI](https://img.shields.io/pypi/v/dockerhub-api)](https://pypi.org/project/dockerhub-api/)
![MCP Server](https://badge.mcpx.dev?type=server 'MCP Server')
[![License](https://img.shields.io/pypi/l/dockerhub-api)](https://github.com/Knuckles-Team/dockerhub-api/blob/main/LICENSE)
[![GitHub](https://img.shields.io/badge/source-GitHub-181717?logo=github)](https://github.com/Knuckles-Team/dockerhub-api)

## Overview

`dockerhub-api` wraps the Docker Hub REST surface with typed, deterministic MCP
tools and an optional Pydantic-AI agent server. It provides:

- **`Api`** — a Python client (`dockerhub_api.api_client.Api`) composed from
  per-domain mixins covering repositories and tags, immutable tags, personal and
  organization access tokens, organization members/settings/invites, teams,
  audit logs, and SCIM 2.0 provisioning.
- **Action-routed MCP tools** — seven consolidated, togglable tool modules
  (`hub_auth`, `hub_repos`, `hub_org`, `hub_teams`, `hub_audit`, `hub_scim`,
  `hub_admin`) that minimize token overhead in LLM contexts.
- **An A2A agent server** — a Pydantic-AI graph agent (console script
  `dockerhub-agent`) that calls the MCP tool surface and exposes an AG-UI web
  interface.

The connector remains inactive when credentials are absent: configure
`DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` (password, PAT `dckr_pat_*`, or org
access token) to connect it to Docker Hub.

## Explore the documentation

<div class="grid cards" markdown>

- :material-rocket-launch: **[Installation](installation.md)** — pip, source, extras, and the prebuilt Docker image.
- :material-server-network: **[Deployment](deployment.md)** — run the MCP and agent servers, Docker Compose.
- :material-console: **[Usage](usage.md)** — the MCP tools, the `Api` client, and the CLI.
- :material-docker: **[Backing Platform](platform.md)** — Docker Hub accounts, tokens, and org governance.
- :material-sitemap: **[Overview](overview.md)** — the action-routed tool surface and architecture.
- :material-tag-multiple: **[Concepts](concepts.md)** — the `CONCEPT:HUB-*` registry.

</div>

## Quick start

```bash
pip install "dockerhub-api[mcp]"
dockerhub-mcp                        # stdio MCP server (default transport)
```

Connect it to Docker Hub:

```bash
export DOCKERHUB_USERNAME=youruser
export DOCKERHUB_TOKEN=dckr_pat_xxx
dockerhub-mcp --transport streamable-http --host 0.0.0.0 --port 8000
```

See **[Installation](installation.md)** and **[Deployment](deployment.md)** for
the full walkthrough.

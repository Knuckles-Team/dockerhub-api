# Deployment

<!-- BEGIN GENERATED: deployment-options -->
## Deployment Options

`dockerhub-api` exposes its MCP server (console script `dockerhub-mcp`) four ways. Pick the row that
matches where the server runs relative to your MCP client, then copy the matching
`mcp_config.json` below. Replace the `<your-…>` placeholders with the values from the **Configuration / Environment Variables** section.

| # | Option | Transport | Where it runs | `mcp_config.json` key |
|---|--------|-----------|---------------|------------------------|
| 1 | stdio | `stdio` | client launches a subprocess | `command` |
| 2 | Streamable-HTTP (local) | `streamable-http` | a local network port | `command` or `url` |
| 3 | Local container / uv | `stdio` or `streamable-http` | Docker / Podman / uv on this host | `command` or `url` |
| 4 | Remote URL | `streamable-http` | a remote host behind Caddy | `url` |

### 1. stdio (local subprocess)

The client launches the server over stdio via `uvx` — best for local IDEs
(Cursor, Claude Desktop, VS Code):

```json
{
  "mcpServers": {
    "dockerhub-mcp": {
      "command": "uvx",
      "args": ["--from", "dockerhub-api", "dockerhub-mcp"],
      "env": {
        "DOCKERHUB_URL": "<your-dockerhub_url>",
        "DOCKER_REGISTRY_URL": "<your-docker_registry_url>",
        "DOCKER_SCOUT_URL": "<your-docker_scout_url>"
      }
    }
  }
}
```

### 2. Streamable-HTTP (local process)

Run the server as a long-lived HTTP process:

```bash
uvx --from dockerhub-api dockerhub-mcp --transport streamable-http --host 0.0.0.0 --port 8000
curl -s http://localhost:8000/health        # {"status":"OK"}
```

Then either let the client launch it:

```json
{
  "mcpServers": {
    "dockerhub-mcp": {
      "command": "uvx",
      "args": ["--from", "dockerhub-api", "dockerhub-mcp", "--transport", "streamable-http", "--port", "8000"],
      "env": {
        "TRANSPORT": "streamable-http",
        "HOST": "0.0.0.0",
        "PORT": "8000",
        "DOCKERHUB_URL": "<your-dockerhub_url>",
        "DOCKER_REGISTRY_URL": "<your-docker_registry_url>",
        "DOCKER_SCOUT_URL": "<your-docker_scout_url>"
      }
    }
  }
}
```

…or connect to the already-running process by URL:

```json
{
  "mcpServers": {
    "dockerhub-mcp": { "url": "http://localhost:8000/mcp" }
  }
}
```

### 3. Local container / uv

**(a) Launch a container directly from `mcp_config.json`** (stdio over the container —
no ports to manage). Swap `docker` for `podman` for a daemonless runtime:

```json
{
  "mcpServers": {
    "dockerhub-mcp": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "TRANSPORT=stdio",
        "-e", "DOCKERHUB_URL=<your-dockerhub_url>",
        "-e", "DOCKER_REGISTRY_URL=<your-docker_registry_url>",
        "-e", "DOCKER_SCOUT_URL=<your-docker_scout_url>",
        "knucklessg1/dockerhub-api:latest"
      ]
    }
  }
}
```

**(b) Run a local streamable-http container, then connect by URL:**

```bash
docker run -d --name dockerhub-mcp -p 8000:8000 \
  -e TRANSPORT=streamable-http \
  -e PORT=8000 \
  -e DOCKERHUB_URL="<your-dockerhub_url>" \
  -e DOCKER_REGISTRY_URL="<your-docker_registry_url>" \
  -e DOCKER_SCOUT_URL="<your-docker_scout_url>" \
  knucklessg1/dockerhub-api:latest
# or, from a clone of this repo:
docker compose -f docker/mcp.compose.yml up -d
```

```json
{
  "mcpServers": {
    "dockerhub-mcp": { "url": "http://localhost:8000/mcp" }
  }
}
```

**(c) From a local checkout with `uv`:**

```bash
uv run dockerhub-mcp --transport streamable-http --port 8000
```

### 4. Remote URL (deployed behind Caddy)

When the server is deployed remotely (e.g. as a Docker service) and published through
Caddy on the internal `*.arpa` zone, connect with the `"url"` key — no local process or
image required:

```json
{
  "mcpServers": {
    "dockerhub-mcp": { "url": "http://dockerhub-mcp.arpa/mcp" }
  }
}
```

Caddy reverse-proxies `http://dockerhub-mcp.arpa` to the container's `:8000`
streamable-http listener; `http://dockerhub-mcp.arpa/health` returns
`{"status":"OK"}` when the service is live.
<!-- END GENERATED: deployment-options -->

## MCP server (standalone)

```bash
pip install "dockerhub-api[mcp]"
export DOCKERHUB_USERNAME=youruser
export DOCKERHUB_TOKEN=dckr_pat_xxx
dockerhub-mcp --transport streamable-http --host 0.0.0.0 --port 8000
```

Transports: `stdio` (default), `streamable-http`, `sse`.

## Docker Compose — MCP only

```bash
cp .env.example .env       # fill in DOCKERHUB_* values
docker compose -f docker/mcp.compose.yml up -d
```

## Docker Compose — MCP + A2A agent

```bash
docker compose -f docker/agent.compose.yml up -d
```

This starts:

- `dockerhub-api-mcp` on port **8000** (streamable-http, `/health` endpoint)
- `dockerhub-api-agent` on port **9018** (A2A + AG-UI web interface), pointed at
  the MCP service via `MCP_URL`

## MCP client registration

Register the server in any MCP-capable client using the template in
`mcp_config.json`:

```json
{
  "mcpServers": {
    "dockerhub-api": {
      "command": "uv",
      "args": ["run", "dockerhub-mcp"],
      "env": {
        "DOCKERHUB_USERNAME": "youruser",
        "DOCKERHUB_TOKEN": "dckr_pat_xxx",
        "DOCKERHUB_ALLOW_DESTRUCTIVE": "False"
      }
    }
  }
}
```

## Security posture

- Leave `DOCKERHUB_ALLOW_DESTRUCTIVE=False` in shared deployments; enable it only
  for operator sessions that genuinely need deletes or org-settings writes.
- Prefer **organization access tokens** scoped with `TYPE_REPO` path globs over
  account-wide PATs for CI/CD.
- Eunomia policies and OTEL/Langfuse tracing are available through the
  agent-utilities server bootstrap (see `.env.example`).

## Debug image

`docker/debug.Dockerfile` builds the package from the working tree with dev
tooling (uv, ripgrep, starship) for interactive debugging:

```bash
docker build -f docker/debug.Dockerfile -t dockerhub-api:debug .
docker run --rm -it dockerhub-api:debug bash
```

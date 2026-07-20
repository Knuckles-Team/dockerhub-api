# Deployment

<!-- BEGIN GENERATED: deployment-options -->
## Deployment Options

`dockerhub-api` supports local stdio, a loopback-only development listener, a
least-privilege stdio container, and a remote authenticated HTTPS boundary.
Provider endpoint, credential, selector, identity, and trust material are supplied
at runtime through `AgentConfig`; none is stored in this repository.

### Installed stdio process

```json
{
  "mcpServers": {
    "dockerhub": {
      "command": "dockerhub-mcp",
      "args": [],
      "env": {"MCP_TOOL_MODE": "intent"}
    }
  }
}
```

### Loopback development listener

```bash
dockerhub-mcp --transport streamable-http --host 127.0.0.1 --port 8000
```

Do not expose this listener beyond loopback. Network deployments require direct TLS
or an explicitly trusted TLS-terminating ingress, configured authentication, exact
`MCP_ALLOWED_HOSTS`, and an exact trusted-proxy CIDR policy.

### Least-privilege local container

```bash
docker run -i --rm \
  --read-only \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  --pids-limit=256 \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m \
  -e TRANSPORT=stdio \
  registry.example.invalid/dockerhub-api@sha256:<digest> dockerhub-mcp
```

The operator projects the selected AgentConfig profile into the process at runtime;
the image remains immutable and contains no environment connection profile.

### Remote authenticated HTTPS endpoint

```json
{
  "mcpServers": {
    "dockerhub": {"url": "https://service.example.invalid/mcp"}
  }
}
```

Store the real remote URL, outbound identity reference, and TLS-profile reference in
`AgentConfig`, not in MCP client JSON or documentation.
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

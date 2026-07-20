# Installation

## Requirements

- Python **3.11 – 3.14**
- A Docker Hub account plus a credential: account password, personal access token
  (`dckr_pat_*`), or organization access token.

## From PyPI

```bash
pip install dockerhub-api              # API client only
pip install "dockerhub-api[mcp]"       # + MCP server
pip install "dockerhub-api[agent]"     # + A2A agent server
pip install "dockerhub-api[all]"       # everything
```

## From source

```bash
git clone https://github.com/Knuckles-Team/dockerhub-api.git
cd dockerhub-api
pip install -e .[all]
```

## Docker image

```bash
docker pull example/dockerhub-api@sha256:<digest>
docker run --rm -e DOCKERHUB_USERNAME=youruser -e DOCKERHUB_TOKEN=dckr_pat_xxx \
  -e TRANSPORT=streamable-http -p 8000:8000 example/dockerhub-api@sha256:<digest>
```

## Configuration

Copy `.env.example` to `.env` and fill in your values:

| Variable | Default | Purpose |
|---|---|---|
| `DOCKERHUB_URL` | `https://hub.docker.com` | API base URL |
| `DOCKERHUB_USERNAME` | — | Identifier (username or org) for token exchange |
| `DOCKERHUB_TOKEN` | — | Secret: password, PAT `dckr_pat_*`, or org access token |
| `DOCKERHUB_JWT` | — | Optional pre-minted bearer (skips the exchange) |
| `DOCKERHUB_TLS_PROFILE` | `system` | TLS verification |
| `DOCKERHUB_ALLOW_DESTRUCTIVE` | `False` | Enable deletes and org-settings writes |
| `AUTHTOOL` … `ADMINTOOL` | `True` | Per-module MCP tool toggles |

## Verify

```bash
dockerhub-mcp --help
dockerhub-agent --help
python -m dockerhub_api.mcp_server --help
```

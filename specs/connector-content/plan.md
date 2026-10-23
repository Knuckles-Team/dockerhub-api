# CONN-DOCKERHUB-API-CONNECTOR-CONTENT — Design and implementation plan

Governing spec: [spec.md](spec.md).

## Architecture

`pyproject.toml` declares `dockerhub-mcp` as the connector identity. `create_mcp_server` resolves the packaged content of `dockerhub_api` from it.

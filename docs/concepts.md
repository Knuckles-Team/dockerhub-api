# Concept Registry — dockerhub-api

> **Prefix**: `CONCEPT:DH-OS.governance.hub-x` | **Version**: 0.1.0

This connector inherits the ecosystem bridge concept `ECO-4.0`
(connector parity standard) from
[`agent-utilities`](https://github.com/Knuckles-Team/agent-utilities/blob/main/docs/overview.md),
alongside `ECO-4.1` (MCP & Universal Skills) and `AU-ECO.toolkit.journey-map-narrative` (A2A Network).

The `CONCEPT:DH-OS.governance.hub-x` registry tracks the load-bearing capabilities of this
connector. Markers appear in module docstrings so traceability sweeps can map
concept → code.

| Concept | Name | Where it lives |
|---|---|---|
| `CONCEPT:DH-OS.audit.core-wrapper-api-is` | **Core wrapper** — raw `httpx` client over `https://hub.docker.com`, per-domain mixins, pydantic input/response models, uniform `{status_code, data, rate_limit}` envelope, typed error mapping. | `dockerhub_api/api/api_client_base.py`, `dockerhub_api/api_client.py`, `dockerhub_api/dockerhub_input_models.py`, `dockerhub_api/dockerhub_response_models.py` |
| `CONCEPT:DH-OS.identity.jwt-auth-lifecycle-endpoint` | **JWT auth lifecycle** — `TokenManager` mints a short-lived JWT from `POST /v2/auth/token` (password / PAT / OAT), caches it, refreshes before expiry, re-mints once on 401; PAT + OAT CRUD; deprecated login + 2FA retained for parity. | `dockerhub_api/auth.py`, `dockerhub_api/api/api_client_auth.py`, `dockerhub_api/api/api_client_access_tokens.py`, `dockerhub_api/api/api_client_org_access_tokens.py` |
| `CONCEPT:DH-OS.governance.rate-limit-telemetry-every` | **Rate-limit telemetry** — `X-RateLimit-*` capture on every response, bounded `Retry-After` backoff on 429, `hub_admin.rate_limit` surface. | `dockerhub_api/api/api_client_base.py`, `dockerhub_api/mcp/mcp_admin.py` |
| `CONCEPT:DH-OS.identity.destructive-action-gating-member` | **Destructive-action gating** — deletes (tokens, groups, members, invites) and org-settings writes blocked unless `DOCKERHUB_ALLOW_DESTRUCTIVE=True`; repository creation deliberately ungated. | `dockerhub_api/api/api_client_base.py` (`_guard_destructive`), `dockerhub_api/api/api_client_orgs.py`, `dockerhub_api/api/api_client_groups.py` |
| `CONCEPT:DH-OS.audit.action-routed-mcp-surface` | **Action-routed MCP surface** — nine consolidated, togglable tools with secret redaction and error envelopes. | `dockerhub_api/mcp/`, `dockerhub_api/mcp_server.py` |
| `CONCEPT:DH-OS.governance.scim-provisioning-all-requests` | **SCIM provisioning** — `application/scim+json` media type, SCIM-style `startIndex`/`count` pagination, discovery + user lifecycle. | `dockerhub_api/api/api_client_scim.py`, `dockerhub_api/mcp/mcp_scim.py` |
| `CONCEPT:DH-OS.governance.a2a-agent-server-pydantic` | **A2A agent server** — Pydantic-AI graph agent over the MCP tool surface with AG-UI web interface. | `dockerhub_api/agent_server.py`, `a2a.json`, `dockerhub_api/main_agent.json` |
| `CONCEPT:DH-OS.identity.registry-v2-scoped-token` | **Registry v2 client + scoped-token auth** — separate `registry-1.docker.io` client; per-repository, challenge-based bearer tokens (`401 WWW-Authenticate` → token service → retry) via `RegistryTokenManager`; tags, manifests, blobs, digest resolution, multi-arch platform/config inspection. | `dockerhub_api/auth.py` (`RegistryTokenManager`, `get_registry_client`), `dockerhub_api/api/api_client_registry_base.py`, `dockerhub_api/api/api_client_registry.py` |
| `CONCEPT:DH-OS.governance.registry-v2-mcp-tool` | **Registry v2 MCP tool** — `hub_registry` action surface (toggle `REGISTRYTOOL`) over the registry client. | `dockerhub_api/mcp/mcp_registry.py` |
| `CONCEPT:DH-OS.governance.oci-referrers-attestation-discovery` | **OCI Referrers / attestation discovery** — `GET /v2/{repo}/referrers/{digest}` surfaces SBOM and provenance attestation manifests referencing an image. | `dockerhub_api/api/api_client_registry.py` (`list_referrers`) |
| `CONCEPT:DH-OS.governance.chunked-blob-push-upload` | **Chunked blob push** — upload session (`POST`→`PATCH`→`PUT`), cross-repo `mount`, and `put_manifest`; all gated by `DOCKERHUB_ALLOW_DESTRUCTIVE`. | `dockerhub_api/api/api_client_registry.py` |
| `CONCEPT:DH-OS.identity.docker-scout-client-cve` | **Docker Scout client + MCP tool** — `api.scout.docker.com` CVE/vulnerability, SBOM, image summary, compare, and policy evaluation, reusing the Hub JWT; `hub_scout` action surface (toggle `SCOUTTOOL`). | `dockerhub_api/auth.py` (`get_scout_client`), `dockerhub_api/api/api_client_scout.py`, `dockerhub_api/mcp/mcp_scout.py` |

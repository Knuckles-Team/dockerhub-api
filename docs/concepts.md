# Concepts

The `CONCEPT:HUB-1.x` registry tracks the load-bearing capabilities of this
connector. Markers appear in module docstrings so traceability sweeps can map
concept → code.

| Concept | Name | Where it lives |
|---|---|---|
| `CONCEPT:HUB-1.0` | **Core wrapper** — raw `httpx` client over `https://hub.docker.com`, per-domain mixins, pydantic input/response models, uniform `{status_code, data, rate_limit}` envelope, typed error mapping. | `dockerhub_api/api/api_client_base.py`, `dockerhub_api/api_client.py`, `dockerhub_api/dockerhub_input_models.py`, `dockerhub_api/dockerhub_response_models.py` |
| `CONCEPT:HUB-1.1` | **JWT auth lifecycle** — `TokenManager` mints a short-lived JWT from `POST /v2/auth/token` (password / PAT / OAT), caches it, refreshes before expiry, re-mints once on 401; PAT + OAT CRUD; deprecated login + 2FA retained for parity. | `dockerhub_api/auth.py`, `dockerhub_api/api/api_client_auth.py`, `dockerhub_api/api/api_client_access_tokens.py`, `dockerhub_api/api/api_client_org_access_tokens.py` |
| `CONCEPT:HUB-1.2` | **Rate-limit telemetry** — `X-RateLimit-*` capture on every response, bounded `Retry-After` backoff on 429, `hub_admin.rate_limit` surface. | `dockerhub_api/api/api_client_base.py`, `dockerhub_api/mcp/mcp_admin.py` |
| `CONCEPT:HUB-1.3` | **Destructive-action gating** — deletes (tokens, groups, members, invites) and org-settings writes blocked unless `DOCKERHUB_ALLOW_DESTRUCTIVE=True`; repository creation deliberately ungated. | `dockerhub_api/api/api_client_base.py` (`_guard_destructive`), `dockerhub_api/api/api_client_orgs.py`, `dockerhub_api/api/api_client_groups.py` |
| `CONCEPT:HUB-1.4` | **Action-routed MCP surface** — seven consolidated, togglable tools with secret redaction and error envelopes. | `dockerhub_api/mcp/`, `dockerhub_api/mcp_server.py` |
| `CONCEPT:HUB-1.5` | **SCIM provisioning** — `application/scim+json` media type, SCIM-style `startIndex`/`count` pagination, discovery + user lifecycle. | `dockerhub_api/api/api_client_scim.py`, `dockerhub_api/mcp/mcp_scim.py` |
| `CONCEPT:HUB-1.6` | **A2A agent server** — Pydantic-AI graph agent over the MCP tool surface with AG-UI web interface. | `dockerhub_api/agent_server.py`, `a2a.json`, `dockerhub_api/main_agent.json` |

# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-06-11

### Added

- **CONCEPT:HUB-1.0** — core Docker Hub API wrapper (`dockerhub_api.api_client.Api`):
  raw `httpx` client over `https://hub.docker.com` composed from per-domain mixins
  (auth, personal access tokens, org access tokens, audit logs, orgs, repositories,
  groups/teams, SCIM) with pydantic input/response models and a uniform
  `{status_code, data, rate_limit}` envelope.
- **CONCEPT:HUB-1.1** — JWT auth lifecycle: `TokenManager` mints a short-lived JWT
  from `POST /v2/auth/token` (password / PAT `dckr_pat_*` / org access token),
  caches it, refreshes before expiry, and transparently re-mints once on 401.
  Deprecated `POST /v2/users/login` + `POST /v2/users/2fa-login` retained for parity.
- **CONCEPT:HUB-1.2** — rate-limit telemetry: `X-RateLimit-*` headers captured on
  every response and exposed in results; HTTP 429 retried with bounded
  `Retry-After` backoff.
- **CONCEPT:HUB-1.3** — destructive-action gating: deletes (tokens, groups, members,
  invites) and org-settings writes are disabled unless
  `DOCKERHUB_ALLOW_DESTRUCTIVE=True`; repository creation stays allowed (primary
  provisioning use case).
- **CONCEPT:HUB-1.4** — action-routed MCP surface: consolidated, togglable tools
  `hub_auth`, `hub_repos`, `hub_org`, `hub_teams`, `hub_audit`, `hub_scim`,
  `hub_admin` with secret redaction in tool results.
- **CONCEPT:HUB-1.5** — SCIM 2.0 provisioning with `application/scim+json` media
  type and SCIM-style `startIndex`/`count` pagination.
- **CONCEPT:HUB-1.6** — A2A agent server (`dockerhub-agent`) over the MCP tool
  surface via agent-utilities `create_agent_server`.
- Comprehensive mocked-`httpx` test suite (no live Docker Hub calls), Docker
  packaging, MkDocs documentation site, and fleet-standard repo scaffolding.

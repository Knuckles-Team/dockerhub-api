# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2026-11-12

### Changed
- Destructive operations use the SDK's one declaration and guard: the 14 delete, remove, organization-settings and registry-write operations are declared with `destructive_operation`, and every destructive tool takes the standard `confirm` argument. The `DOCKERHUB_ALLOW_DESTRUCTIVE` setting, the `allow_destructive` client option and `DestructiveOperationError` are removed; the one operator setting is `SCION_ALLOW_DESTRUCTIVE`.
- Require `scion-sdk[mcp]>=0.10.2,<0.11`.

## [1.3.10] - 2026-11-06

### Changed
- Connector surface: full agent-definition prompts (operator, release engineer, organization administrator, security analyst), task workflow skills that name every served tool, tool-use contracts for all 82 tools, data locations and business roles.
- Require `scion-sdk>=0.9.0`; `uv.lock` relocked.
- `dockerhub_get_audit_logs` takes `audit_action` (was `action`) for the audit event filter.

### Removed
- The unregistered action-routed `hub_*` tool modules; the typed per-operation tools remain the surface.

## [1.3.9] - 2026-10-30

### Changed
- Require `scion-sdk>=0.6.4,<0.7.0`; `uv.lock` relocked.

## [1.3.6] - 2026-10-24

### Changed
- Central connector migration: requires `agent-connector-sdk>=0.5.4`; server bootstrap, version, containers, ontology artifacts, security scaffold and pre-commit config are provided centrally.

## [1.3.5] - 2026-10-24

### Changed
- Central connector migration: requires `agent-connector-sdk>=0.5.4`; server bootstrap, version, containers, ontology artifacts, security scaffold and pre-commit config are provided centrally.

## [Unreleased]

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
- Complete mocked-`httpx` test suite (no live Docker Hub calls), Docker
  packaging, MkDocs documentation site, and fleet-standard repo scaffolding.

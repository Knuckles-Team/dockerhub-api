# Backing Platform (Docker Hub)

Unlike most connectors in this fleet, the backing platform is **Docker Hub
itself** (`https://hub.docker.com`) — a hosted SaaS registry that cannot be
self-deployed. This page covers what you need on the Docker Hub side.

## Account & credentials

1. Create a Docker Hub account (or use an organization-owned service account).
2. Mint a credential for the connector — in order of preference:
   - **Organization access token (OAT)** — *Organization settings → Access
     tokens*. Scope it to `TYPE_REPO` resources with path globs (e.g. `acme/*`)
     and the minimal scopes (`repo:read`, `repo:write`, `repo:admin`).
   - **Personal access token (PAT)** — *Account settings → Personal access
     tokens* (`dckr_pat_*`), with scopes `repo:admin` / `repo:write` /
     `repo:read` / `repo:public_read`.
   - **Account password** — works with `POST /v2/auth/token` but is the weakest
     option; 2FA-enabled accounts should use tokens.
3. Configure the connector:

```bash
export DOCKERHUB_USERNAME=youruser        # identifier (user or org)
export DOCKERHUB_TOKEN=dckr_pat_xxx       # the secret from step 2
```

The connector exchanges the credential for a **short-lived JWT** via
`POST /v2/auth/token` and refreshes it automatically before expiry.

## API surface & versioning

- Base URL: `https://hub.docker.com` — this is the **Hub management API
  (v2-beta)**, distinct from the registry pull/push protocol
  (`registry-1.docker.io`).
- Reference: [Docker Hub API documentation](https://docs.docker.com/reference/api/hub/latest/).
- `POST /v2/users/login` is **deprecated** upstream; the connector implements it
  (plus `POST /v2/users/2fa-login`) for parity but uses `/v2/auth/token` itself.

## Rate limits

Docker Hub applies per-endpoint rate limits, surfaced via
`X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers.
The connector exposes the latest snapshot in every result envelope and via the
`hub_admin` tool's `rate_limit` action, and honors `Retry-After` on HTTP 429
with a bounded backoff.

## Organization governance features

| Feature | Requires | Connector surface |
|---|---|---|
| Members, roles, invites | Team/Business plan | `hub_org` |
| Groups (teams) + repo permissions | Team/Business plan | `hub_teams`, `hub_repos` (`assign_group`) |
| Audit logs | Team/Business plan | `hub_audit` |
| Registry access management (restricted images) | Business plan | `hub_org` (`get_settings`/`update_settings`) |
| SCIM 2.0 user provisioning | Business plan + SSO | `hub_scim` |
| Immutable tags | Docker Hub feature rollout | `hub_repos` (`set_immutable_tags`/`verify_immutable_tags`) |

Calls against features your plan does not include return HTTP 403, which the
connector maps to `UnauthorizedError`.

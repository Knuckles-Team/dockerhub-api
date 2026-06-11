# Usage — API / CLI / MCP

`dockerhub-api` exposes the same capability three ways: as **MCP tools** an agent
calls, as a **Python API** (`Api`) you import, and as a **CLI** (the `dockerhub-mcp`
and `dockerhub-agent` entry points). The complete action-routed tool surface is
documented in [Overview](overview.md).

## As an MCP server

Once [deployed](deployment.md), the server registers consolidated, action-routed
tool modules. Each module is independently togglable with a `*TOOL` environment
flag:

| Group | Tool modules |
|---|---|
| Tokens & identity | `hub_auth`, `hub_admin` |
| Images | `hub_repos` |
| Organization | `hub_org`, `hub_teams` |
| Governance | `hub_audit`, `hub_scim` |

Example agent prompts that map onto these tools:

- *"Create a private repo `acme/release-images` for the next release"* →
  `hub_repos` (`create`)
- *"Which tags does `acme/app` have, and is `v1.0.0` immutable?"* →
  `hub_repos` (`list_tags`, `verify_immutable_tags`)
- *"Invite jane@example.com and dev2 to the platform team — dry run first"* →
  `hub_org` (`bulk_invite` with `dry_run: true`)
- *"Show the audit trail for repo deletions last week"* → `hub_audit` (`logs`)
- *"How close are we to the rate limit?"* → `hub_admin` (`rate_limit`)

Tool calls take an `action` and a `params_json` object:

```json
{
  "action": "list",
  "params_json": "{\"namespace\": \"acme\", \"ordering\": \"-last_updated\", \"page_size\": 25}"
}
```

## As a Python API

Build a client from the environment with `get_client()`:

```python
from dockerhub_api.auth import get_client

api = get_client()   # reads DOCKERHUB_URL / DOCKERHUB_USERNAME / DOCKERHUB_TOKEN

# Reads
repos = api.get_repositories(namespace="acme", name="app", ordering="-last_updated")
tags = api.get_repository_tags(namespace="acme", repository="app", page=1, page_size=50)
members = api.get_org_members(org="acme", role="member")
logs = api.get_audit_logs(account="acme", action="repo.create",
                          from_date="2026-06-01T00:00:00Z")

# Provisioning
api.create_repository(namespace="acme", name="release-images", is_private=True)
api.assign_repository_group(namespace="acme", repository="release-images",
                            group_id=7, permission="write")
api.bulk_invite(org="acme", invitees=["jane@example.com"], team="platform",
                dry_run=True)

# Tokens
pat = api.create_access_token(token_label="ci", scopes=["repo:write"])
print(pat["data"]["token"])   # plaintext appears exactly once

# Telemetry
print(api.rate_limit)         # {'limit': 180, 'remaining': 173, 'reset': ...}
print(api.whoami())           # local JWT introspection — no network call
```

Or construct it explicitly:

```python
from dockerhub_api.api_client import Api

api = Api(url="https://hub.docker.com", username="youruser",
          password="dckr_pat_xxx", allow_destructive=True)
api.delete_access_token(uuid="...")   # destructive — requires the flag
```

### Error mapping

| HTTP status | Exception |
|---|---|
| 400 / 404 | `ParameterError` |
| 401 | `AuthError` (after one transparent token refresh) |
| 403 | `UnauthorizedError` |
| 429 (retries exhausted) | `ApiError` |
| other 4xx/5xx | `ApiError` |
| gated destructive call | `DestructiveOperationError` |

## As a CLI

```bash
dockerhub-mcp                                  # stdio transport
dockerhub-mcp --transport streamable-http --host 0.0.0.0 --port 8000
dockerhub-agent --mcp-url http://localhost:8000/mcp --web
```

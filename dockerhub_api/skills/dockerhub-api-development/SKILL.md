---
name: dockerhub-api-development
skill_type: skill
description: >-
  Develop, test, and publish the dockerhub-api connector without breaking its
  typed Docker Hub API contract, packaged content, spec delivery dashboard, or
  governed Pages workflow. Use when changing connector code, docs, skills,
  workflows, or repository-owned specs.
license: MIT
tags: [dockerhub, connector, development, testing, pages, specs]
metadata:
  author: Genius
  version: '0.1.0'
---
# Docker Hub API Development

Use this skill for changes inside the dockerhub-api package. The connector
exposes Docker Hub management, registry, Scout, and knowledge-graph operations
through typed HTTP clients, action-routed MCP tools, an A2A agent, and packaged
resource content. Keep those surfaces aligned when a change crosses a boundary.

## Repository map

- dockerhub_api/api/ contains domain client mixins composed into the Api facade.
- dockerhub_api/auth.py owns JWT minting, caching, refresh, and client setup.
- dockerhub_api/mcp/ registers domain tools and keeps actions routed through the
  corresponding client method.
- dockerhub_api/skills/, prompts/, ontology/, and connectors/ are packaged
  resources exposed by the connector entry point.
- specs/connector-content/ and specs/connector-identity/ are the source
  specifications; their status.json files are generated evidence, never hand
  edited.

## Before editing

1. Work from a real worktree based on the repository's current origin/main.
2. Find the owning row under specs/ before adding behavior, and preserve the
   existing CONCEPT: registry when a domain capability is involved.
3. Trace a changed action from its Pydantic input model through the MCP router,
   client mixin, auth lifecycle, and response envelope. Do not duplicate an
   existing HTTP path.
4. Keep credentials and external Docker Hub calls out of tests; extend the
   existing MockHub transport and assert the request and redacted result.

## Implementation contract

- Preserve the dockerhub-mcp connector name and the uniform
  status_code/data/rate_limit response envelope.
- Keep destructive operations behind DockerHubApiBase._guard_destructive and
  never persist or return bearer tokens except the documented one-time create
  response.
- Use Pydantic input and response models, action-routed tools, and the shared
  agent-utilities server/agent factories.
- Add or update a focused test when behavior changes. Cover invalid action or
  parameters and the successful response shape.
- Keep all package resources under the existing package-data globs so an sdist
  and wheel expose the same skills, prompts, ontology, agent data, and
  connector manifest.

## Rapid delivery: the 5-minute contract

Specs are already designed. Deliver one small, reviewable change at a time.

- Start with one owning requirement and state its proof before editing.
- Keep a slice to one connector concern: source code, one test seam, one
  workflow/configuration repair, or one substantive skill.
- Run the smallest relevant tests first, then the repository pre-commit suite
  on the candidate worktree. Fix warnings and failures rather than bypassing a
  hook.
- Record the exact source and test commands in the commit or review handoff.
- Never claim a Pages or spec row from a YAML marker alone: the dashboard config,
  generated status records, successful exact-source workflow, and published
  page must agree.
- Commit only reviewed paths with an explicit path list. Never stage a whole
  shared checkout, credentials, caches, generated logs, or temporary output.

## Spec delivery and Pages

The canonical Pages caller is .github/workflows/pages.yml. This repository uses
the docs/ content source, so the caller must pass content_source: docs, enable
spec_dashboard_enabled, and point spec_dashboard_config at
.github/spec-dashboard.json. The push path set must include specs/**, the
dashboard config, and the Pages workflow itself in addition to documentation
paths. Keep the config versioned and bounded to specs/*/status.json; the
central renderer owns the HTML layout.

Regenerate status evidence with the pipeline hook when a spec changes, inspect
the resulting diff, and verify that no status row was advanced without a real
implementation or test receipt. The Pages proof is complete only after the
published run uses the candidate commit and /spec-delivery/ serves the
candidate snapshot.

## Verification

From the repository root:

    pre-commit run --all-files
    python -m pytest tests -q

Prefer focused tests for the touched module while iterating. For Pages changes,
also run the central dashboard renderer against a task-local output directory
and verify the config parses, status files are discovered, and the result
contains the connector content and identity records.

## Safety

Never commit .env files, tokens, raw Docker Hub identifiers, or generated site
output. Never make live Docker Hub calls from tests. Preserve destructive
gating and secret redaction. If a dependency or packaged metadata change is
necessary, update the lockfile in the same slice and explain why in the review.

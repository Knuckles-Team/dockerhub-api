"""In-memory MCP server validation: tool registration, action routing,
secret redaction, destructive gating, and toggles."""

import json
import sys

import httpx
import pytest
from fastmcp import Client

import dockerhub_api.auth as hub_auth_module
from tests.conftest import BASE_URL, make_registry_api, make_scout_api

EXPECTED_TOOLS = {
    "dockerhub_get_repositories",
    "dockerhub_get_groups",
    "dockerhub_get_org_members",
    "dockerhub_bulk_invite",
    "dockerhub_delete_group",
    "dockerhub_create_auth_token",
    "dockerhub_create_access_token",
    "dockerhub_get_access_tokens",
    "dockerhub_get_audit_logs",
    "dockerhub_get_scim_users",
    "dockerhub_registry_list_tags",
    "dockerhub_registry_inspect",
    "dockerhub_registry_put_manifest",
    "dockerhub_scout_get_cves",
    "dockerhub_ingest_repositories",
}


@pytest.fixture
def mcp_instance(hub, registry, scout, monkeypatch):
    from dockerhub_api.api_client import Api

    def fake_get_client(**_kwargs):
        return Api(
            url=BASE_URL,
            username="tester",
            password="dckr_pat_unit",  # nosec B105 B106 — fake test credential
            transport=httpx.MockTransport(hub.handler),
        )

    monkeypatch.setattr(hub_auth_module, "get_client", fake_get_client)
    monkeypatch.setattr(
        hub_auth_module, "get_registry_client", lambda **_k: make_registry_api(registry)
    )
    monkeypatch.setattr(
        hub_auth_module, "get_scout_client", lambda **_k: make_scout_api(scout)
    )
    monkeypatch.setattr(sys, "argv", ["dockerhub-mcp"])
    from dockerhub_api.mcp_server import get_mcp_instance

    mcp, _args, _middlewares, registered = get_mcp_instance()
    return mcp


def tool_payload(result):
    """Extract the structured payload from a fastmcp CallToolResult."""
    if getattr(result, "data", None) is not None:
        return result.data
    if getattr(result, "structured_content", None) is not None:
        return result.structured_content
    return json.loads(result.content[0].text)


async def _call(mcp, name, args):
    async with Client(mcp) as client:
        return tool_payload(await client.call_tool(name, args))


async def test_all_tools_registered(mcp_instance):
    async with Client(mcp_instance) as client:
        tools = await client.list_tools()
    names = {tool.name for tool in tools}
    assert EXPECTED_TOOLS <= names
    for tool in (t for t in tools if "ingest" not in t.name):
        assert set(tool.inputSchema.get("properties", {})) != {"params_json"}


async def test_get_repositories(mcp_instance):
    payload = await _call(mcp_instance, "dockerhub_get_repositories", {"namespace": "acme"})
    assert payload["status_code"] == 200
    assert payload["data"]["results"][0]["name"] == "app"
    assert payload["rate_limit"]["limit"] == 180


async def test_auth_jwt_redacted_but_pat_visible_on_create(mcp_instance):
    minted = await _call(
        mcp_instance,
        "dockerhub_create_auth_token",
        {"identifier": "tester", "secret": "dckr_pat_unit"},  # nosec B105 B106 — fake test credential
    )
    created = await _call(
        mcp_instance,
        "dockerhub_create_access_token",
        {"token_label": "ci", "scopes": ["repo:read"]},
    )
    listed = await _call(mcp_instance, "dockerhub_get_access_tokens", {})
    assert minted["data"]["access_token"] == "***redacted***"
    assert created["data"]["token"] == "dckr_pat_PLAINTEXT"
    assert "dckr_pat_PLAINTEXT" not in json.dumps(listed)


async def test_audit_and_scim(mcp_instance):
    audit = await _call(mcp_instance, "dockerhub_get_audit_logs", {"account": "acme"})
    scim = await _call(
        mcp_instance, "dockerhub_get_scim_users", {"start_index": 1, "count": 5}
    )
    assert audit["data"]["logs"]
    assert scim["data"]["totalResults"] == 1


def test_redact_secrets_helper():
    from dockerhub_api.mcp import REDACTED, redact_secrets

    data = {
        "access_token": "abc",  # nosec B105 B106 — fake test credential
        "nested": [{"password": "p", "token": "keepme"}],  # nosec B105 B106 — fake test credential
        "ok": 1,
    }
    redacted = redact_secrets(data)
    assert redacted["access_token"] == REDACTED
    assert redacted["nested"][0]["password"] == REDACTED
    assert redacted["nested"][0]["token"] == "keepme"  # not a SECRET_KEY by default
    assert redacted["ok"] == 1


async def test_registry_operations(mcp_instance):
    tags = await _call(mcp_instance, "dockerhub_registry_list_tags", {"repo": "nginx"})
    inspected = await _call(
        mcp_instance,
        "dockerhub_registry_inspect",
        {"repo": "nginx", "reference": "latest"},
    )
    assert tags["data"]["tags"] == ["latest", "1.0", "1.1"]
    assert len(inspected["data"]["platforms"]) == 2


async def test_scout_operations(mcp_instance):
    cves = await _call(
        mcp_instance,
        "dockerhub_scout_get_cves",
        {"repo": "myorg/app", "reference": "v1"},
    )
    assert cves["data"]["cves"][0]["id"] == "CVE-2026-0001"


async def test_org_and_teams_operations(mcp_instance):
    members = await _call(mcp_instance, "dockerhub_get_org_members", {"org": "acme"})
    invites = await _call(
        mcp_instance,
        "dockerhub_bulk_invite",
        {"org": "acme", "invitees": ["new@x.io"], "dry_run": True},
    )
    teams = await _call(mcp_instance, "dockerhub_get_groups", {"org": "acme"})
    assert members["data"]["count"] == 2
    assert invites["data"]["dry_run"] is True
    assert teams["data"]["results"][0]["name"] == "platform"


async def test_destructive_operations_are_annotated(mcp_instance):
    async with Client(mcp_instance) as client:
        tools = {t.name: t for t in await client.list_tools()}
    assert tools["dockerhub_delete_group"].annotations.destructiveHint is True
    assert tools["dockerhub_get_repositories"].annotations.readOnlyHint is True

"""In-memory MCP server validation: tool registration, action routing,
secret redaction, destructive gating, and toggles."""

import json
import sys

import httpx
import pytest
from fastmcp import Client

import dockerhub_api.auth as hub_auth_module
from tests.conftest import BASE_URL

EXPECTED_TOOLS = {
    "hub_auth",
    "hub_repos",
    "hub_org",
    "hub_teams",
    "hub_audit",
    "hub_scim",
    "hub_admin",
}


@pytest.fixture
def mcp_instance(hub, monkeypatch):
    from dockerhub_api.api_client import Api

    def fake_get_client(**_kwargs):
        return Api(
            url=BASE_URL,
            username="tester",
            password="dckr_pat_unit",  # nosec B105 B106 — fake test credential
            transport=httpx.MockTransport(hub.handler),
        )

    monkeypatch.setattr(hub_auth_module, "get_client", fake_get_client)
    monkeypatch.setattr(sys, "argv", ["dockerhub-mcp"])
    from dockerhub_api.mcp_server import get_mcp_instance

    mcp, _args, _middlewares, registered = get_mcp_instance()
    assert len(registered) == len(EXPECTED_TOOLS)
    return mcp


def tool_payload(result):
    """Extract the structured payload from a fastmcp CallToolResult."""
    if getattr(result, "data", None) is not None:
        return result.data
    if getattr(result, "structured_content", None) is not None:
        return result.structured_content
    return json.loads(result.content[0].text)


async def test_all_tools_registered(mcp_instance):
    async with Client(mcp_instance) as client:
        tools = await client.list_tools()
    assert {tool.name for tool in tools} == EXPECTED_TOOLS


async def test_hub_repos_list_action(mcp_instance):
    async with Client(mcp_instance) as client:
        result = await client.call_tool(
            "hub_repos",
            {"action": "list", "params_json": json.dumps({"namespace": "acme"})},
        )
    payload = tool_payload(result)
    assert payload["status_code"] == 200
    assert payload["data"]["results"][0]["name"] == "app"
    assert payload["rate_limit"]["limit"] == 180


async def test_unknown_action_is_reported(mcp_instance):
    async with Client(mcp_instance) as client:
        result = await client.call_tool("hub_repos", {"action": "explode"})
    payload = tool_payload(result)
    assert payload["error"]["type"] == "UnknownAction"
    assert "explode" in payload["error"]["message"]


async def test_invalid_params_json_is_reported(mcp_instance):
    async with Client(mcp_instance) as client:
        result = await client.call_tool(
            "hub_repos", {"action": "list", "params_json": "{not json"}
        )
    payload = tool_payload(result)
    assert "Invalid params_json" in str(payload["error"])


async def test_destructive_action_blocked_via_mcp(mcp_instance):
    async with Client(mcp_instance) as client:
        result = await client.call_tool(
            "hub_teams",
            {
                "action": "delete",
                "params_json": json.dumps({"org": "acme", "group_name": "platform"}),
            },
        )
    payload = tool_payload(result)
    assert payload["error"]["type"] == "DestructiveOperationError"


async def test_auth_jwt_redacted_but_pat_visible_on_create(mcp_instance):
    async with Client(mcp_instance) as client:
        minted = await client.call_tool(
            "hub_auth",
            {
                "action": "create_token",
                "params_json": json.dumps(
                    {"identifier": "tester", "secret": "dckr_pat_unit"}  # nosec B105 B106 — fake test credential
                ),
            },
        )
        created = await client.call_tool(
            "hub_auth",
            {
                "action": "create_pat",
                "params_json": json.dumps(
                    {"token_label": "ci", "scopes": ["repo:read"]}  # nosec B105 B106 — fake test credential
                ),
            },
        )
        listed = await client.call_tool(
            "hub_auth", {"action": "list_pats", "params_json": "{}"}
        )
    assert tool_payload(minted)["data"]["access_token"] == "***redacted***"
    assert tool_payload(created)["data"]["token"] == "dckr_pat_PLAINTEXT"
    assert "dckr_pat_PLAINTEXT" not in json.dumps(tool_payload(listed))


async def test_hub_admin_whoami(mcp_instance):
    async with Client(mcp_instance) as client:
        result = await client.call_tool(
            "hub_admin", {"action": "whoami", "params_json": "{}"}
        )
    payload = tool_payload(result)
    assert payload["data"]["authenticated"] is True


async def test_hub_audit_and_scim_actions(mcp_instance):
    async with Client(mcp_instance) as client:
        audit = await client.call_tool(
            "hub_audit",
            {"action": "logs", "params_json": json.dumps({"account": "acme"})},
        )
        scim = await client.call_tool(
            "hub_scim",
            {
                "action": "list_users",
                "params_json": json.dumps({"start_index": 1, "count": 5}),
            },
        )
    assert tool_payload(audit)["data"]["logs"]
    assert tool_payload(scim)["data"]["totalResults"] == 1


def test_tool_toggles_disable_modules(hub, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["dockerhub-mcp"])
    monkeypatch.setenv("SCIMTOOL", "False")
    monkeypatch.setenv("AUDITTOOL", "False")
    from dockerhub_api.mcp_server import get_mcp_instance

    _mcp, _args, _middlewares, registered = get_mcp_instance()
    assert "SCIMTOOL" not in registered
    assert "AUDITTOOL" not in registered
    assert "REPOSTOOL" in registered


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


async def test_hub_org_and_teams_actions(mcp_instance):
    async with Client(mcp_instance) as client:
        members = await client.call_tool(
            "hub_org",
            {"action": "list_members", "params_json": json.dumps({"org": "acme"})},
        )
        invites = await client.call_tool(
            "hub_org",
            {
                "action": "bulk_invite",
                "params_json": json.dumps(
                    {"org": "acme", "invitees": ["new@x.io"], "dry_run": True}
                ),
            },
        )
        teams = await client.call_tool(
            "hub_teams",
            {"action": "list", "params_json": json.dumps({"org": "acme"})},
        )
    assert tool_payload(members)["data"]["count"] == 2
    assert tool_payload(invites)["data"]["dry_run"] is True
    assert tool_payload(teams)["data"]["results"][0]["name"] == "platform"

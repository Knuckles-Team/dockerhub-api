"""CONN-DOCKERHUB-API-CONNECTOR-CONTENT-R003: destructive operations use the SDK's one declaration and guard."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import httpx
import pytest
from fastmcp import Client
from scion_sdk.connector import build_server

pytestmark = pytest.mark.spec("CONN-DOCKERHUB-API-CONNECTOR-CONTENT-R003")

DESTRUCTIVE_TOOLS = {
    "dockerhub_delete_access_token": {"uuid": "u1"},
    "dockerhub_delete_group": {"org": "acme", "group_name": "g"},
    "dockerhub_delete_invite": {"invite_id": "i1"},
    "dockerhub_delete_org_access_token": {"org": "acme", "token_id": "t1"},
    "dockerhub_remove_group_member": {
        "org": "acme",
        "group_name": "g",
        "username": "u",
    },
    "dockerhub_remove_org_member": {"org": "acme", "username": "u"},
    "dockerhub_update_org_settings": {"org": "acme", "restricted_images_enabled": True},
    "dockerhub_registry_delete_blob": {
        "repo": "acme/app",
        "digest": "sha256:" + "a" * 64,
    },
    "dockerhub_registry_delete_manifest": {"repo": "acme/app", "reference": "latest"},
    "dockerhub_registry_start_upload": {"repo": "acme/app"},
}


def _server(requests: list[httpx.Request], monkeypatch):
    real = httpx.Client

    def record(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={})

    def client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(record)
        return real(*args, **kwargs)

    monkeypatch.setattr("dockerhub_api.api.api_client_base.httpx.Client", client)
    monkeypatch.setenv("DOCKERHUB_JWT", "jwt")
    monkeypatch.delenv("SCION_ALLOW_DESTRUCTIVE", raising=False)
    with patch("sys.argv", ["dockerhub-mcp"]):
        return build_server("dockerhub_api", command_args=[])[1]


def test_declared_operations_are_destructive_tools_that_ask_first(monkeypatch):
    mcp = _server([], monkeypatch)

    async def _run():
        async with Client(mcp) as client:
            tools = {t.name: t for t in await client.list_tools()}
            for name in DESTRUCTIVE_TOOLS:
                assert tools[name].annotations.destructive_hint is True, name
            for name, tool in tools.items():
                properties = tool.input_schema["properties"]
                assert "allow_destructive" not in properties, name
                if tool.annotations and tool.annotations.destructive_hint:
                    assert "confirm" in properties, name

    asyncio.run(_run())


@pytest.mark.parametrize("name", sorted(DESTRUCTIVE_TOOLS))
def test_unconfirmed_call_sends_no_request(name, monkeypatch):
    requests: list[httpx.Request] = []
    mcp = _server(requests, monkeypatch)

    async def _run():
        async with Client(mcp) as client:
            refused = await client.call_tool(
                name, DESTRUCTIVE_TOOLS[name], raise_on_error=False
            )
            assert refused.structured_content["cancelled"] is True

    asyncio.run(_run())
    assert requests == []


def test_confirmed_call_sends_one_request(monkeypatch):
    requests: list[httpx.Request] = []
    mcp = _server(requests, monkeypatch)

    async def _run():
        async with Client(mcp) as client:
            await client.call_tool(
                "dockerhub_delete_access_token", {"uuid": "u1", "confirm": True}
            )

    asyncio.run(_run())
    assert [r.method for r in requests] == ["DELETE"]

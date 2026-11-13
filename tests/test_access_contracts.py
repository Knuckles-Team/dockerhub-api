"""Access contracts bind fields the served read tools return."""

import json
import sys
from pathlib import Path

import httpx
import pytest
from fastmcp import Client
from scion_sdk.access_contract import parse_access_contracts

import dockerhub_api.auth as hub_auth_module
from tests.conftest import MockHub, make_api

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "dockerhub_api/ontology"


def _contracts():
    text = (ONTOLOGY / "access_contracts.ttl").read_text()
    return {c.entity: c for c in parse_access_contracts(text)}


def _recording(entity):
    return json.loads((ROOT / f"tests/recordings/{entity}.json").read_text())


async def _serve(monkeypatch, contract, arguments, recording):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/token"):
            return httpx.Response(200, json={"access_token": "fixture-token"})
        return httpx.Response(200, json=recording)

    api = make_api(MockHub(), transport=httpx.MockTransport(handler))
    monkeypatch.setattr(hub_auth_module, "get_client", lambda **_k: api)
    monkeypatch.setattr(sys, "argv", ["dockerhub-mcp"])
    from scion_sdk.connector import build_server

    _, mcp = build_server("dockerhub_api", command_args=[])
    async with Client(mcp) as client:
        result = await client.call_tool(contract.operation, arguments)
    return result.data if result.data is not None else result.structured_content


def _dig(payload, path):
    for part in path.split("."):
        payload = payload[part]
    return payload


@pytest.mark.spec("CONN-DOCKERHUB-API-CONNECTOR-CONTENT-R002")
@pytest.mark.parametrize(
    ("entity", "arguments", "fields"),
    [
        (
            "repository",
            {"namespace": "acme"},
            {"name", "last_updated", "pull_count"},
        ),
        (
            "tag",
            {"namespace": "acme", "repository": "app"},
            {"repository", "last_updated"},
        ),
    ],
)
async def test_competency_contracts_certified(monkeypatch, entity, arguments, fields):
    contract = _contracts()[entity]
    recording = _recording(entity)
    ontology = (ONTOLOGY / "dockerhub.ttl").read_text()
    assert contract.access_kind == "mcp_tool"
    assert contract.key_field == "name"
    assert {field for _, field in contract.predicates} == fields
    for prop, _ in contract.predicates:
        local = prop.rsplit("#", 1)[-1]
        assert f":{local} a owl:DatatypeProperty" in ontology
    payload = await _serve(monkeypatch, contract, arguments, recording)
    records = _dig(payload, contract.records_path)
    assert records
    for record in records:
        assert contract.key_field in record
        assert all(field in record for field in fields)


@pytest.mark.spec("CONN-DOCKERHUB-API-CONNECTOR-CONTENT-R002")
def test_repository_and_tag_contracts():
    contracts = _contracts()
    assert set(contracts) == {"repository", "tag"}
    assert contracts["repository"].operation == "dockerhub_get_repositories"
    assert contracts["tag"].operation == "dockerhub_get_repository_tags"

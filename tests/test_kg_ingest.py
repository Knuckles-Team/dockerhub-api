"""Native epistemic-graph typed-node ingestion -- Wire-First coverage for dockerhub-api.

Exercises the real ``ingest_entities`` / ``ingest_repositories`` / ``ingest_tags`` seam
against a fake ``agent_connector_sdk.ingest`` transport (no engine required). The real
SDK request builder (``agent_connector_sdk.ingest.request.build_request``) still runs,
so a malformed change set is still caught by the SDK's own contract, not re-derived
here; only the final network commit is faked.
CONCEPT:AU-KG.ingest.enterprise-source-extractor.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from agent_connector_sdk.ingest import IngestError, KnowledgeIngest
from epistemic_graph.generated.source_ingestion import SourceIngestionRequest

from dockerhub_api.kg_ingest import (
    ingest_entities,
    ingest_repositories,
    ingest_tags,
)


class _FakeTransport:
    """Records every submitted request; no epistemic-graph engine required."""

    def __init__(self) -> None:
        self.requests: list[SourceIngestionRequest] = []

    async def source_status(self, _connector: str, _stream: str) -> Any:
        return SimpleNamespace(accepted_checkpoint=None)

    async def submit(self, request: SourceIngestionRequest) -> Any:
        self.requests.append(request)
        return SimpleNamespace(
            affected_count=len(request.records),
            relationship_count=len(request.relationships),
        )

    async def store_blob(self, _data: bytes) -> str:
        raise AssertionError("dockerhub-api ingestion carries no media")


@pytest.fixture
def ingest() -> tuple[KnowledgeIngest, _FakeTransport]:
    transport = _FakeTransport()
    return KnowledgeIngest(transport, loop=None), transport


@pytest.mark.asyncio
async def test_ingest_entities_writes_nodes_and_edges(ingest):
    service, transport = ingest
    res = await ingest_entities(
        [
            {"id": "a", "node_type": "Repository", "name": "r"},
            {"id": "b", "node_type": "Namespace"},
        ],
        [{"source": "a", "target": "b", "relationship": "inNamespace"}],
        ingest=service,
    )
    assert res == {"nodes": 2, "edges": 1}
    assert len(transport.requests) == 1
    request = transport.requests[0]
    record_ids = {record.record_id for record in request.records}
    assert record_ids == {"a", "b"}
    a_record = next(r for r in request.records if r.record_id == "a")
    assert a_record.payload["name"] == "r"
    assert request.relationships[0].relation_reference.endswith(
        "resources/Repository/relations/inNamespace"
    )


@pytest.mark.asyncio
async def test_ingest_repositories_maps_repo_namespace_and_images(ingest):
    service, transport = ingest
    res = await ingest_repositories(
        [
            {
                "name": "api-gateway",
                "namespace": "mycorp",
                "description": "edge",
                "is_private": True,
                "pull_count": 1200,
                "star_count": 5,
                "tags": [
                    {
                        "name": "v1.4.2",
                        "full_size": 4096,
                        "images": [
                            {
                                "digest": "sha256:abc",
                                "architecture": "amd64",
                                "os": "linux",
                                "size": 4096,
                            }
                        ],
                    }
                ],
            }
        ],
        ingest=service,
    )
    # repo + namespace + image = 3 nodes
    assert res == {"nodes": 3, "edges": 3}
    request = transport.requests[0]
    repo_id = "dockerhub:repository:mycorp/api-gateway"
    ns_id = "dockerhub:namespace:mycorp"
    img_id = "dockerhub:image:mycorp/api-gateway:v1.4.2"
    repo_record = next(r for r in request.records if r.record_id == repo_id)
    assert repo_record.payload["isPrivate"] is True
    assert repo_record.payload["pullCount"] == 1200
    ns_record = next(r for r in request.records if r.record_id == ns_id)
    assert ns_record.payload["name"] == "mycorp"
    img_record = next(r for r in request.records if r.record_id == img_id)
    assert img_record.payload["digest"] == "sha256:abc"
    assert img_record.payload["architecture"] == "amd64"
    relation_refs = {rel.relation_reference.rsplit("/", 1)[-1] for rel in request.relationships}
    assert relation_refs == {"inNamespace", "imageOf", "hasImage"}


@pytest.mark.asyncio
async def test_ingest_tags_maps_images_with_repo_anchor(ingest):
    service, transport = ingest
    res = await ingest_tags(
        "mycorp",
        "api-gateway",
        [{"name": "latest", "digest": "sha256:def", "full_size": 100}],
        ingest=service,
    )
    # one image + the repository anchor
    assert res == {"nodes": 2, "edges": 2}
    request = transport.requests[0]
    img_id = "dockerhub:image:mycorp/api-gateway:latest"
    repo_id = "dockerhub:repository:mycorp/api-gateway"
    assert any(r.record_id == img_id for r in request.records)
    assert any(r.record_id == repo_id for r in request.records)


@pytest.mark.asyncio
async def test_ingest_rejects_legacy_structural_fields(ingest):
    service, _transport = ingest
    with pytest.raises(IngestError, match="node_type"):
        await ingest_entities([{"id": "legacy", "type": "Legacy"}], ingest=service)


@pytest.mark.asyncio
async def test_ingest_empty_is_rejected(ingest):
    service, _transport = ingest
    with pytest.raises(IngestError, match="at least one entity"):
        await ingest_entities([], ingest=service)
    with pytest.raises(IngestError, match="at least one entity"):
        await ingest_tags("mycorp", "api-gateway", [], ingest=service)

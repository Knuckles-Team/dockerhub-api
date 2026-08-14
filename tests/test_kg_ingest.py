"""Native epistemic-graph typed-node ingestion — Wire-First coverage.

Exercises the real ``ingest_entities`` / ``ingest_repositories`` / ``ingest_tags`` seams
with a fake engine client (no engine required), asserting the txn add_node/commit + edge
calls and the Docker Hub record → :Repository/:ContainerImage/:Namespace mapping.
CONCEPT:AU-KG.ingest.enterprise-source-extractor.
"""

from __future__ import annotations

from typing import Any

import msgpack
import pytest
from agent_utilities.knowledge_graph.memory.native_ingest import NativeIngestError
from agent_utilities.security.brain_context import ActorContext, use_actor
from agent_utilities.models.company_brain import ActorType
from agent_utilities.knowledge_graph.core.session import GraphSession, use_session

from dockerhub_api.kg_ingest import (
    ingest_entities,
    ingest_repositories,
    ingest_tags,
)


@pytest.fixture(autouse=True)
def _governed_session():
    actor = ActorContext(
        actor_id="subject:opaque:synthetic",
        actor_type=ActorType.AUTOMATED_SERVICE,
        roles=(),
        tenant_id="tenant:opaque:synthetic",
        authenticated=True,
    )
    session = GraphSession(
        actor=actor,
        tenant=actor.tenant_id,
        scopes=frozenset({"kg:write"}),
        graph="graph:opaque:synthetic",
        policy_version="policy:opaque:synthetic",
        audience="epistemic-graph",
    )
    with use_actor(actor), use_session(session):
        yield


class _FakeNodes:
    def __init__(self) -> None:
        self.values: dict[str, dict[str, Any]] = {}

    def properties(self, node_id: str) -> dict[str, Any] | None:
        return self.values.get(node_id)

    def list(self) -> list[tuple[str, dict[str, Any]]]:
        return list(self.values.items())


class _FakeChanges:
    def __init__(self, nodes: _FakeNodes) -> None:
        self.nodes = nodes
        self.edges: list[tuple[str, str, dict[str, Any]]] = []
        self.applied: list[dict[str, Any]] = []
        self.records: dict[str, dict[str, Any]] = {}
        self.versions: dict[str, dict[str, Any]] = {}

    def get(self, envelope_id: str) -> dict[str, Any] | None:
        return self.records.get(envelope_id)

    def content_version(self, object_id: str) -> dict[str, Any] | None:
        return self.versions.get(object_id)

    def cursor(self, _source: str, _partition: str = "") -> None:
        return None

    def apply(self, envelope: dict[str, Any]) -> dict[str, Any]:
        self.applied.append(envelope)
        mutation = envelope["mutation"]
        for operation in mutation["operations"]:
            method = operation["method"]
            params = method["params"]
            properties = msgpack.unpackb(params["properties_msgpack"], raw=False)
            if method["method"] == "AddNode":
                self.nodes.values[params["node_id"]] = properties
            elif method["method"] == "AddEdge":
                self.edges.append(
                    (params["source_id"], params["target_id"], properties)
                )
        version = envelope["content_version"]
        self.versions[version["object_id"]] = version
        self.records[envelope["envelope_id"]] = envelope
        return {
            "batch_id": mutation["batch_id"],
            "replayed": False,
            "projection_pending": False,
        }


class _FakeRdf:
    def validate_shacl(self, _shapes: str, _data_graph: str) -> dict[str, Any]:
        return {"conforms": True, "results": []}


class _FakeClient:
    def __init__(self) -> None:
        self.nodes = _FakeNodes()
        self.changes = _FakeChanges(self.nodes)
        self.rdf = _FakeRdf()

    @staticmethod
    def supports(operation: str) -> bool:
        return operation == "ApplyChangeEnvelope"


def test_ingest_entities_writes_nodes_and_edges():
    c = _FakeClient()
    res = ingest_entities(
        [
            {"id": "a", "node_type": "Repository", "name": "r"},
            {"id": "b", "node_type": "Namespace"},
        ],
        [{"source": "a", "target": "b", "relationship": "inNamespace"}],
        client=c,
    )
    assert res == {"nodes": 2, "edges": 1}
    assert len(c.changes.applied) == 1
    assert set(c.nodes.values) == {"a", "b"}
    # provenance is stamped
    assert c.nodes.values["a"]["source"] == "dockerhub-api"
    assert c.nodes.values["a"]["domain"] == "dockerhub"
    assert c.changes.edges == [("a", "b", {"relationship": "inNamespace"})]


def test_ingest_repositories_maps_repo_namespace_and_images():
    c = _FakeClient()
    res = ingest_repositories(
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
        client=c,
    )
    # repo + namespace + image = 3 nodes
    assert res == {"nodes": 3, "edges": 3}
    repo_id = "dockerhub:repository:mycorp/api-gateway"
    ns_id = "dockerhub:namespace:mycorp"
    img_id = "dockerhub:image:mycorp/api-gateway:v1.4.2"
    assert c.nodes.values[repo_id]["node_type"] == "Repository"
    assert c.nodes.values[repo_id]["isPrivate"] is True
    assert c.nodes.values[repo_id]["pullCount"] == 1200
    assert c.nodes.values[ns_id]["node_type"] == "Namespace"
    assert c.nodes.values[img_id]["node_type"] == "ContainerImage"
    assert c.nodes.values[img_id]["digest"] == "sha256:abc"
    assert c.nodes.values[img_id]["architecture"] == "amd64"
    # edges: repo->ns (inNamespace), img->repo (imageOf), repo->img (hasImage)
    assert (repo_id, ns_id, {"relationship": "inNamespace"}) in c.changes.edges
    assert (img_id, repo_id, {"relationship": "imageOf"}) in c.changes.edges
    assert (repo_id, img_id, {"relationship": "hasImage"}) in c.changes.edges


def test_ingest_tags_maps_images_with_repo_anchor():
    c = _FakeClient()
    res = ingest_tags(
        "mycorp",
        "api-gateway",
        [{"name": "latest", "digest": "sha256:def", "full_size": 100}],
        client=c,
    )
    # one image + the repository anchor
    assert res == {"nodes": 2, "edges": 2}
    img_id = "dockerhub:image:mycorp/api-gateway:latest"
    repo_id = "dockerhub:repository:mycorp/api-gateway"
    assert c.nodes.values[img_id]["node_type"] == "ContainerImage"
    assert c.nodes.values[repo_id]["node_type"] == "Repository"


def test_ingest_rejects_legacy_structural_fields():
    with pytest.raises(NativeIngestError, match="canonical node_type"):
        ingest_entities([{"id": "legacy", "type": "Legacy"}], client=_FakeClient())


def test_ingest_empty_is_rejected():
    with pytest.raises(NativeIngestError, match="at least one entity"):
        ingest_entities([], client=_FakeClient())
    with pytest.raises(NativeIngestError, match="at least one entity"):
        ingest_tags("mycorp", "api-gateway", [], client=_FakeClient())

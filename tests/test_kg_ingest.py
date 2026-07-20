"""Native epistemic-graph typed-node ingestion — Wire-First coverage.

Exercises the real ``ingest_entities`` / ``ingest_repositories`` / ``ingest_tags`` seams
with a fake engine client (no engine required), asserting the txn add_node/commit + edge
calls and the Docker Hub record → :Repository/:ContainerImage/:Namespace mapping.
CONCEPT:AU-KG.ingest.enterprise-source-extractor.
"""

from __future__ import annotations

import pytest
from agent_utilities.knowledge_graph.memory.native_ingest import NativeIngestError

from dockerhub_api.kg_ingest import (
    ingest_entities,
    ingest_repositories,
    ingest_tags,
)


class _FakeTxn:
    def __init__(self):
        self.nodes = {}
        self.edges = []
        self.committed = False

    def begin(self, graph=None):
        self.graph = graph
        return "txn-1"

    def add_node(self, txn, node_id, props):
        self.nodes[node_id] = props

    def add_edge(self, txn, src, dst, props):
        self.edges.append((src, dst, props))

    def commit(self, txn):
        self.committed = True
        return True



class _FakeClient:
    def __init__(self):
        self.txn = _FakeTxn()


def test_ingest_entities_writes_nodes_and_edges():
    c = _FakeClient()
    res = ingest_entities(
        [
            {"id": "a", "node_type": "Repository", "name": "r"},
            {"id": "b", "node_type": "Namespace"},
        ],
        [{"source": "a", "target": "b", "relationship": "inNamespace"}],
        client=c,
        graph="__commons__",
    )
    assert res == {"nodes": 2, "edges": 1}
    assert c.txn.committed is True
    assert set(c.txn.nodes) == {"a", "b"}
    # provenance is stamped
    assert c.txn.nodes["a"]["source"] == "dockerhub-api"
    assert c.txn.nodes["a"]["domain"] == "dockerhub"
    assert c.txn.edges == [("a", "b", {"relationship": "inNamespace"})]


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
        graph="__commons__",
    )
    # repo + namespace + image = 3 nodes
    assert res == {"nodes": 3, "edges": 3}
    repo_id = "dockerhub:repository:mycorp/api-gateway"
    ns_id = "dockerhub:namespace:mycorp"
    img_id = "dockerhub:image:mycorp/api-gateway:v1.4.2"
    assert c.txn.nodes[repo_id]["node_type"] == "Repository"
    assert c.txn.nodes[repo_id]["isPrivate"] is True
    assert c.txn.nodes[repo_id]["pullCount"] == 1200
    assert c.txn.nodes[ns_id]["node_type"] == "Namespace"
    assert c.txn.nodes[img_id]["node_type"] == "ContainerImage"
    assert c.txn.nodes[img_id]["digest"] == "sha256:abc"
    assert c.txn.nodes[img_id]["architecture"] == "amd64"
    # edges: repo->ns (inNamespace), img->repo (imageOf), repo->img (hasImage)
    assert (repo_id, ns_id, {"relationship": "inNamespace"}) in c.txn.edges
    assert (img_id, repo_id, {"relationship": "imageOf"}) in c.txn.edges
    assert (repo_id, img_id, {"relationship": "hasImage"}) in c.txn.edges


def test_ingest_tags_maps_images_with_repo_anchor():
    c = _FakeClient()
    res = ingest_tags(
        "mycorp",
        "api-gateway",
        [{"name": "latest", "digest": "sha256:def", "full_size": 100}],
        client=c,
        graph="__commons__",
    )
    # one image + the repository anchor
    assert res == {"nodes": 2, "edges": 2}
    img_id = "dockerhub:image:mycorp/api-gateway:latest"
    repo_id = "dockerhub:repository:mycorp/api-gateway"
    assert c.txn.nodes[img_id]["node_type"] == "ContainerImage"
    assert c.txn.nodes[repo_id]["node_type"] == "Repository"


def test_ingest_rejects_legacy_structural_fields():
    with pytest.raises(NativeIngestError, match="canonical node_type"):
        ingest_entities([{"id": "legacy", "type": "Legacy"}], client=_FakeClient())


def test_ingest_empty_is_rejected():
    with pytest.raises(NativeIngestError, match="at least one entity"):
        ingest_entities([], client=_FakeClient())
    with pytest.raises(NativeIngestError, match="at least one entity"):
        ingest_tags("mycorp", "api-gateway", [], client=_FakeClient())

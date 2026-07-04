"""Native epistemic-graph typed-node ingestion — Wire-First coverage.

Exercises the real ``ingest_entities`` / ``ingest_repositories`` / ``ingest_tags`` seams
with a fake engine client (no engine required), asserting the txn add_node/commit + edge
calls and the Docker Hub record → :Repository/:ContainerImage/:Namespace mapping.
CONCEPT:AU-KG.ingest.enterprise-source-extractor.
"""

from __future__ import annotations

from dockerhub_api.kg_ingest import (
    ingest_entities,
    ingest_repositories,
    ingest_tags,
)


class _FakeTxn:
    def __init__(self):
        self.nodes = {}
        self.committed = False

    def begin(self, graph=None):
        self.graph = graph
        return "txn-1"

    def add_node(self, txn, node_id, props):
        self.nodes[node_id] = props

    def commit(self, txn):
        self.committed = True
        return True


class _FakeEdges:
    def __init__(self):
        self.edges = []

    def add(self, src, dst, props):
        self.edges.append((src, dst, props))


class _FakeClient:
    def __init__(self):
        self.txn = _FakeTxn()
        self.edges = _FakeEdges()


def test_ingest_entities_writes_nodes_and_edges():
    c = _FakeClient()
    res = ingest_entities(
        [
            {"id": "a", "type": "Repository", "name": "r"},
            {"id": "b", "type": "Namespace"},
        ],
        [{"source": "a", "target": "b", "type": "inNamespace"}],
        client=c,
        graph="__commons__",
    )
    assert res == {"nodes": 2, "edges": 1}
    assert c.txn.committed is True
    assert set(c.txn.nodes) == {"a", "b"}
    # provenance is stamped
    assert c.txn.nodes["a"]["source"] == "dockerhub-api"
    assert c.txn.nodes["a"]["domain"] == "dockerhub"
    assert c.edges.edges == [("a", "b", {"type": "inNamespace"})]


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
    assert c.txn.nodes[repo_id]["type"] == "Repository"
    assert c.txn.nodes[repo_id]["isPrivate"] is True
    assert c.txn.nodes[repo_id]["pullCount"] == 1200
    assert c.txn.nodes[ns_id]["type"] == "Namespace"
    assert c.txn.nodes[img_id]["type"] == "ContainerImage"
    assert c.txn.nodes[img_id]["digest"] == "sha256:abc"
    assert c.txn.nodes[img_id]["architecture"] == "amd64"
    # edges: repo->ns (inNamespace), img->repo (imageOf), repo->img (hasImage)
    assert (repo_id, ns_id, {"type": "inNamespace"}) in c.edges.edges
    assert (img_id, repo_id, {"type": "imageOf"}) in c.edges.edges
    assert (repo_id, img_id, {"type": "hasImage"}) in c.edges.edges


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
    assert c.txn.nodes[img_id]["type"] == "ContainerImage"
    assert c.txn.nodes[repo_id]["type"] == "Repository"


def test_ingest_noops_without_engine():
    # No injected client + no reachable engine -> clean no-op.
    assert ingest_entities([{"id": "a", "type": "Repository"}]) is None


def test_ingest_empty_is_noop():
    assert ingest_entities([], client=_FakeClient()) is None
    assert ingest_repositories([], client=_FakeClient()) is None
    assert ingest_tags("ns", "repo", [], client=_FakeClient()) is None

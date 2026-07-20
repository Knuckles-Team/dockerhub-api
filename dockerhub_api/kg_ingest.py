"""Native epistemic-graph ingestion for Docker Hub records (typed graph nodes).

CONCEPT:AU-KG.ingest.enterprise-source-extractor. The dockerhub-api connector natively
pushes its data into the ONE epistemic-graph knowledge graph as **typed OWL nodes**
(``:Repository``, ``:ContainerImage``, ``:Namespace``, …) + links, matching the classes
federated by ``dockerhub_api.ontology``.

This is a thin mapper over the required
``agent_utilities.knowledge_graph.memory.native_ingest`` authority. Node ids follow
``dockerhub:<class>:<externalId>``; ``node_type`` on each entity matches a class in
``dockerhub.ttl``.
"""

from __future__ import annotations

from typing import Any

from agent_utilities.knowledge_graph.memory.native_ingest import (
    ingest_documents as _native_ingest_documents,
)
from agent_utilities.knowledge_graph.memory.native_ingest import (
    ingest_entities as _native_ingest_entities,
)

_SOURCE = "dockerhub-api"
_DOMAIN = "dockerhub"
def ingest_entities(
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]] | None = None,
    *,
    source: str = _SOURCE,
    domain: str = _DOMAIN,
    client: Any | None = None,
    graph: str | None = None,
) -> dict[str, int]:
    """Write typed OWL nodes (+ edges) into epistemic-graph.

    Uses canonical ``node_type`` / ``relationship`` structural fields.
    """
    return _native_ingest_entities(
        entities,
        relationships,
        source=source,
        domain=domain,
        client=client,
        graph=graph,
    )


def ingest_documents(
    docs: list[dict[str, Any]],
    *,
    source: str = _SOURCE,
    domain: str = _DOMAIN,
    client: Any | None = None,
    graph: str | None = None,
) -> dict[str, int]:
    """Write text records as ``:Document`` nodes (semantic-search fodder).

    Each doc: ``{"id":..., "text":..., "title"?:..., "source_uri"?:...}``.
    """
    return _native_ingest_documents(
        docs, source=source, domain=domain, client=client, graph=graph
    )


def _image_entities(
    repo_id: str,
    namespace: str,
    repository: str,
    tags: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Map a repository's tags → ``:ContainerImage`` nodes (+ ``:imageOf`` edges)."""
    entities: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    for tag in tags or []:
        name = tag.get("name")
        if not name:
            continue
        images = tag.get("images") or []
        first = images[0] if images else {}
        img_id = f"dockerhub:image:{namespace}/{repository}:{name}"
        entities.append(
            {
                "id": img_id,
                "node_type": "ContainerImage",
                "name": name,
                "repository": f"{namespace}/{repository}",
                "digest": tag.get("digest") or first.get("digest"),
                "architecture": first.get("architecture"),
                "os": first.get("os"),
                "imageSize": tag.get("full_size") or first.get("size"),
                "lastPushed": tag.get("tag_last_pushed") or first.get("last_pushed"),
                "status": tag.get("tag_status"),
                "externalToolId": str(tag.get("id") or img_id),
            }
        )
        relationships.append(
            {"source": img_id, "target": repo_id, "relationship": "imageOf"}
        )
        relationships.append(
            {"source": repo_id, "target": img_id, "relationship": "hasImage"}
        )
    return entities, relationships


def ingest_repositories(
    repositories: list[dict[str, Any]],
    *,
    namespace: str | None = None,
    client: Any | None = None,
    graph: str | None = None,
) -> dict[str, int]:
    """Map Docker Hub repository records → ``:Repository`` (+ ``:Namespace``) nodes.

    Each repository may carry an inline ``tags`` list, which is mapped to
    ``:ContainerImage`` nodes linked back via ``:imageOf`` / ``:hasImage``.
    """
    entities: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    seen_ns: set[str] = set()
    for repo in repositories or []:
        name = repo.get("name")
        ns = repo.get("namespace") or namespace
        if not name or not ns:
            continue
        repo_id = f"dockerhub:repository:{ns}/{name}"
        entities.append(
            {
                "id": repo_id,
                "node_type": "Repository",
                "name": name,
                "namespace": ns,
                "description": repo.get("description"),
                "isPrivate": repo.get("is_private"),
                "pullCount": repo.get("pull_count"),
                "starCount": repo.get("star_count"),
                "repository_type": repo.get("repository_type"),
                "last_updated": repo.get("last_updated"),
                "externalToolId": f"{ns}/{name}",
            }
        )
        ns_id = f"dockerhub:namespace:{ns}"
        if ns not in seen_ns:
            seen_ns.add(ns)
            entities.append({"id": ns_id, "node_type": "Namespace", "name": ns})
        relationships.append(
            {"source": repo_id, "target": ns_id, "relationship": "inNamespace"}
        )
        img_entities, img_rels = _image_entities(
            repo_id, ns, name, repo.get("tags") or []
        )
        entities.extend(img_entities)
        relationships.extend(img_rels)
    return ingest_entities(entities, relationships, client=client, graph=graph)


def ingest_tags(
    namespace: str,
    repository: str,
    tags: list[dict[str, Any]],
    *,
    client: Any | None = None,
    graph: str | None = None,
) -> dict[str, int]:
    """Map a repository's tags → ``:ContainerImage`` nodes linked to their ``:Repository``."""
    repo_id = f"dockerhub:repository:{namespace}/{repository}"
    entities, relationships = _image_entities(repo_id, namespace, repository, tags)
    if not entities:
        return ingest_entities([], client=client, graph=graph)
    # Ensure the repository anchor exists so :imageOf resolves.
    entities.append(
        {
            "id": repo_id,
            "node_type": "Repository",
            "name": repository,
            "namespace": namespace,
            "externalToolId": f"{namespace}/{repository}",
        }
    )
    return ingest_entities(entities, relationships, client=client, graph=graph)

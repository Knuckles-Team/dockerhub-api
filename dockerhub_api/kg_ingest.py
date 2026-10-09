"""Native epistemic-graph ingestion for Docker Hub records (typed graph nodes).

CONCEPT:AU-KG.ingest.enterprise-source-extractor. The dockerhub-api connector natively
pushes its data into the ONE epistemic-graph knowledge graph as **typed OWL nodes**
(``:Repository``, ``:ContainerImage``, ``:Namespace``, …) + links, matching the classes
federated by ``dockerhub_api.ontology``.

This is a thin mapper over ``agent_connector_sdk.ingest`` -- the generated ``SourceIngest``
client, not a local ingestion helper. Node ids follow ``dockerhub:<class>:<externalId>``;
``node_type`` on each entity matches a class in ``dockerhub.ttl``.
"""

from __future__ import annotations

from typing import Any

from agent_connector_sdk.ingest import (
    ChangeSet,
    Document,
    Entity,
    IngestBinding,
    IngestError,
    KnowledgeIngest,
    Relationship,
    current_ingest,
)

_BINDING = IngestBinding(connector="dockerhub-api", stream="dockerhub")

_ENTITY_RESERVED_KEYS = frozenset({"id", "node_type"})
_RELATIONSHIP_RESERVED_KEYS = frozenset({"source", "target", "relationship"})
_DOCUMENT_RESERVED_KEYS = frozenset({"id", "text", "title", "source_uri"})


def _to_entity(record: dict[str, Any]) -> Entity:
    return Entity(
        id=record.get("id"),
        node_type=record.get("node_type"),
        properties={
            key: value
            for key, value in record.items()
            if key not in _ENTITY_RESERVED_KEYS
        },
    )


def _to_relationship(record: dict[str, Any]) -> Relationship:
    properties = {
        key: value
        for key, value in record.items()
        if key not in _RELATIONSHIP_RESERVED_KEYS
    }
    return Relationship(
        source=record["source"],
        target=record["target"],
        relationship=record["relationship"],
        properties=properties or None,
    )


async def ingest_entities(
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]] | None = None,
    *,
    ingest: KnowledgeIngest | None = None,
) -> dict[str, int]:
    """Write typed OWL nodes (+ edges) into epistemic-graph via the SDK ingest facade.

    Uses canonical ``node_type`` / ``relationship`` structural fields.
    """
    if not entities:
        raise IngestError("ingest_entities needs at least one entity")
    change_set = ChangeSet(
        entities=tuple(_to_entity(entity) for entity in entities),
        relationships=tuple(
            _to_relationship(relationship) for relationship in relationships or ()
        ),
    )
    service = ingest or current_ingest()
    receipt = await service.submit(_BINDING, change_set)
    return {"nodes": receipt.affected_count, "edges": receipt.relationship_count}


async def ingest_documents(
    docs: list[dict[str, Any]],
    *,
    ingest: KnowledgeIngest | None = None,
) -> dict[str, int]:
    """Write text records as ``:Document`` nodes (semantic-search fodder).

    Each doc: ``{"id":..., "text":..., "title"?:..., "source_uri"?:...}``.
    """
    if not docs:
        raise IngestError("ingest_documents needs at least one document")
    change_set = ChangeSet(
        documents=tuple(
            Document(
                id=doc["id"],
                text=doc["text"],
                title=doc.get("title"),
                source_uri=doc.get("source_uri"),
                properties={
                    key: value
                    for key, value in doc.items()
                    if key not in _DOCUMENT_RESERVED_KEYS
                },
            )
            for doc in docs
        )
    )
    service = ingest or current_ingest()
    receipt = await service.submit(_BINDING, change_set)
    return {"nodes": receipt.affected_count, "edges": receipt.relationship_count}


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


async def ingest_repositories(
    repositories: list[dict[str, Any]],
    *,
    namespace: str | None = None,
    ingest: KnowledgeIngest | None = None,
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
    return await ingest_entities(entities, relationships, ingest=ingest)


async def ingest_tags(
    namespace: str,
    repository: str,
    tags: list[dict[str, Any]],
    *,
    ingest: KnowledgeIngest | None = None,
) -> dict[str, int]:
    """Map a repository's tags → ``:ContainerImage`` nodes linked to their ``:Repository``."""
    repo_id = f"dockerhub:repository:{namespace}/{repository}"
    entities, relationships = _image_entities(repo_id, namespace, repository, tags)
    if not entities:
        return await ingest_entities([], ingest=ingest)
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
    return await ingest_entities(entities, relationships, ingest=ingest)

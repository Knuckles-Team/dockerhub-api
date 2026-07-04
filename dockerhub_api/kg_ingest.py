"""Native epistemic-graph ingestion for Docker Hub records (typed graph nodes).

CONCEPT:AU-KG.ingest.enterprise-source-extractor. The dockerhub-api connector natively
pushes its data into the ONE epistemic-graph knowledge graph as **typed OWL nodes**
(``:Repository``, ``:ContainerImage``, ``:Namespace``, …) + links, matching the classes
federated by ``dockerhub_api.ontology``.

This is a thin mapper over the shared write primitive
``agent_utilities.knowledge_graph.memory.native_ingest`` — the connector never re-implements
the txn dance. The import is **guarded**: because that primitive is not yet present in every
installed ``agent_utilities``, we fall back to a self-contained txn write over the lightweight
engine client (``GraphComputeEngine()._client``). Either way everything is dependency-/engine-
guarded: with no KG stack or no reachable engine, every entry point **no-ops** (returns
``None``), so the connector runs with zero KG infrastructure. Node ids follow
``dockerhub:<class>:<externalId>``; ``type`` on each entity matches a class in ``dockerhub.ttl``.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("dockerhub_api.kg")

_SOURCE = "dockerhub-api"
_DOMAIN = "dockerhub"
_DEFAULT_GRAPH = "__commons__"


def _fallback_client() -> tuple[Any | None, str]:
    """Return ``(engine_client, graph_name)`` or ``(None, "")`` when unavailable."""
    try:
        from agent_utilities.knowledge_graph.core.graph_compute import (
            GraphComputeEngine,
        )
    except Exception as e:  # noqa: BLE001 — KG stack absent
        logger.debug("KG ingest unavailable (import): %s", e)
        return None, ""
    try:
        engine = GraphComputeEngine()
        client = getattr(engine, "_client", None)
        if client is None:
            return None, ""
        return client, (getattr(engine, "graph_name", None) or _DEFAULT_GRAPH)
    except Exception as e:  # noqa: BLE001 — engine unreachable
        logger.debug("KG ingest: engine unreachable: %s", e)
        return None, ""


def _fallback_write(
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]] | None,
    *,
    client: Any | None,
    graph: str | None,
) -> dict[str, int] | None:
    """Self-contained txn write used when the shared primitive is absent."""
    entities = [e for e in (entities or []) if e.get("id")]
    if not entities:
        return None
    if client is None:
        client, graph = _fallback_client()
    if client is None:
        return None
    graph = graph or _DEFAULT_GRAPH
    try:
        txn = client.txn.begin(graph=graph)
        for ent in entities:
            props = {k: v for k, v in ent.items() if k != "id" and v is not None}
            props.setdefault("source", _SOURCE)
            props.setdefault("domain", _DOMAIN)
            client.txn.add_node(txn, ent["id"], props)
        committed = client.txn.commit(txn)
    except Exception as e:  # noqa: BLE001 — engine/txn failure is non-fatal
        logger.warning("KG ingest: txn failed: %s", e)
        return None
    if not committed:
        logger.warning("KG ingest: txn not committed (conflict)")
        return None
    edges = 0
    for rel in relationships or []:
        try:
            client.edges.add(
                rel["source"], rel["target"], {"type": rel.get("type", "RELATED")}
            )
            edges += 1
        except Exception as e:  # noqa: BLE001 — pure edge link, best-effort
            logger.debug("KG ingest: edge skipped: %s", e)
    logger.info("KG ingest: wrote %d nodes, %d edges", len(entities), edges)
    return {"nodes": len(entities), "edges": edges}


def ingest_entities(
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]] | None = None,
    *,
    source: str = _SOURCE,
    domain: str = _DOMAIN,
    client: Any | None = None,
    graph: str | None = None,
) -> dict[str, int] | None:
    """Write typed OWL nodes (+ edges) into epistemic-graph.

    ``entities``: ``[{"id":..., "type":<owl:Class>, ...props}]``.
    ``relationships``: ``[{"source":id, "target":id, "type":<link>}]``.
    Prefers the shared ``native_ingest`` primitive; falls back to a self-contained
    txn write. Returns ``{"nodes":n, "edges":m}`` or ``None`` (never raises).
    ``client``/``graph`` may be injected (tests); otherwise resolved on demand.
    """
    if not entities:
        return None
    if client is None:
        try:
            from agent_utilities.knowledge_graph.memory.native_ingest import (
                ingest_entities as _shared,
            )

            return _shared(
                entities, relationships, source=source, domain=domain, graph=graph
            )
        except Exception as e:  # noqa: BLE001 — primitive absent / unreachable
            logger.debug("KG ingest: shared primitive unavailable: %s", e)
    return _fallback_write(entities, relationships, client=client, graph=graph)


def ingest_documents(
    docs: list[dict[str, Any]],
    *,
    source: str = _SOURCE,
    domain: str = _DOMAIN,
    client: Any | None = None,
    graph: str | None = None,
) -> dict[str, int] | None:
    """Write text records as ``:Document`` nodes (semantic-search fodder).

    Each doc: ``{"id":..., "text":..., "title"?:..., "source_uri"?:...}``. Prefers the
    shared primitive; falls back to writing ``:Document`` nodes via the txn path.
    """
    docs = [
        d for d in (docs or []) if d.get("id") and (d.get("text") or d.get("content"))
    ]
    if not docs:
        return None
    if client is None:
        try:
            from agent_utilities.knowledge_graph.memory.native_ingest import (
                ingest_documents as _shared,
            )

            return _shared(docs, source=source, domain=domain, graph=graph)
        except Exception as e:  # noqa: BLE001 — primitive absent / unreachable
            logger.debug("KG ingest: shared documents primitive unavailable: %s", e)
    nodes: list[dict[str, Any]] = []
    for doc in docs:
        node = {k: v for k, v in doc.items() if k != "content" and v is not None}
        node["type"] = "Document"
        node["text"] = doc.get("text") or doc.get("content")
        nodes.append(node)
    return _fallback_write(nodes, None, client=client, graph=graph)


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
                "type": "ContainerImage",
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
        relationships.append({"source": img_id, "target": repo_id, "type": "imageOf"})
        relationships.append({"source": repo_id, "target": img_id, "type": "hasImage"})
    return entities, relationships


def ingest_repositories(
    repositories: list[dict[str, Any]],
    *,
    namespace: str | None = None,
    client: Any | None = None,
    graph: str | None = None,
) -> dict[str, int] | None:
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
                "type": "Repository",
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
            entities.append({"id": ns_id, "type": "Namespace", "name": ns})
        relationships.append(
            {"source": repo_id, "target": ns_id, "type": "inNamespace"}
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
) -> dict[str, int] | None:
    """Map a repository's tags → ``:ContainerImage`` nodes linked to their ``:Repository``."""
    repo_id = f"dockerhub:repository:{namespace}/{repository}"
    entities, relationships = _image_entities(repo_id, namespace, repository, tags)
    if not entities:
        return None
    # Ensure the repository anchor exists so :imageOf resolves.
    entities.append(
        {
            "id": repo_id,
            "type": "Repository",
            "name": repository,
            "namespace": namespace,
            "externalToolId": f"{namespace}/{repository}",
        }
    )
    return ingest_entities(entities, relationships, client=client, graph=graph)

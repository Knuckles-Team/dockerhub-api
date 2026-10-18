"""MCP tool for native Docker Hub → epistemic-graph ingestion.

CONCEPT:AU-KG.ingest.enterprise-source-extractor — Wire-First native ingestion surface.
Lists repositories (and optionally their tags) via the real Docker Hub client and pushes
them into the knowledge graph as typed ``:Repository`` / ``:ContainerImage`` / ``:Namespace``
nodes. Best-effort: returns ``{"ingested": None}`` when no engine is reachable.
"""

from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.dependencies import Depends
from pydantic import Field

from dockerhub_api.mcp import get_hub_client


def _envelope_results(envelope: Any) -> list:
    """Unwrap a client response envelope down to its ``results`` list."""
    data = envelope.get("data") if isinstance(envelope, dict) else envelope
    results = (data or {}).get("results") if isinstance(data, dict) else data
    return list(results or [])


def _fetch_repo_tags(client: Any, namespace: str, repo_name: str) -> list:
    """Best-effort tag fetch for one repository; ``[]`` on any failure."""
    try:
        envelope = client.get_repository_tags(namespace=namespace, repository=repo_name)
    except Exception:  # noqa: BLE001 — best-effort tag enrichment
        return []
    return _envelope_results(envelope)


def _enrich_repos_with_tags(client: Any, namespace: str, repos: list) -> None:
    """Attach a ``tags`` list to each repo dict that has a ``name``, in place."""
    for repo in repos:
        rname = repo.get("name")
        if not rname:
            continue
        repo["tags"] = _fetch_repo_tags(client, namespace, rname)


def register_kg_tools(mcp: FastMCP):
    @mcp.tool(tags={"kg"})
    async def dockerhub_ingest_repositories(
        namespace: str = Field(
            description="Docker Hub namespace (user or organization)."
        ),
        name: str | None = Field(
            default=None, description="Filter repositories by name."
        ),
        ordering: str | None = Field(
            default=None, description="Sort order, e.g. 'last_updated'."
        ),
        page: int | None = Field(default=None, description="Page number."),
        page_size: int | None = Field(default=None, description="Results per page."),
        include_tags: bool = Field(
            default=False,
            description="Also ingest each repository's tags as :ContainerImage nodes.",
        ),
        client=Depends(get_hub_client),
        ctx: Context | None = Field(
            default=None, description="MCP context for progress reporting"
        ),
    ) -> Any:
        """Natively ingest Docker Hub repositories into epistemic-graph as typed
        :Repository nodes (with their :Namespace and, optionally, :ContainerImage
        tag nodes). Lists via the real client and pushes through the fast engine
        client. CONCEPT:AU-KG.ingest.enterprise-source-extractor.
        """
        if ctx:
            await ctx.info("Listing Docker Hub repositories for ingestion...")
        from dockerhub_api.kg_ingest import ingest_repositories

        if not namespace:
            return {"error": "namespace is required"}
        kwargs = {
            key: value
            for key, value in {
                "name": name,
                "ordering": ordering,
                "page": page,
                "page_size": page_size,
            }.items()
            if value is not None
        }
        envelope = client.get_repositories(namespace=namespace, **kwargs)
        repos = _envelope_results(envelope)

        if include_tags:
            _enrich_repos_with_tags(client, namespace, repos)

        result = await ingest_repositories(repos, namespace=namespace)
        return {"listed": len(repos), "ingested": result}

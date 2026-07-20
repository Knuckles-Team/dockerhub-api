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

from dockerhub_api.mcp import get_hub_client, parse_params


def register_kg_tools(mcp: FastMCP):
    @mcp.tool(tags={"kg"})
    async def dockerhub_ingest_repositories(
        params_json: str = Field(
            default="{}",
            description=(
                "JSON string of get_repositories params. Requires 'namespace'; "
                "optional 'name', 'ordering', 'page', 'page_size', and "
                "'include_tags' (bool) to also ingest each repo's tags as "
                ":ContainerImage nodes."
            ),
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

        try:
            kwargs = parse_params(params_json)
        except Exception as e:
            return {"error": "Operation failed"}

        namespace = kwargs.get("namespace")
        if not namespace:
            return {"error": "namespace is required"}
        include_tags = bool(kwargs.pop("include_tags", False))

        envelope = client.get_repositories(**kwargs)
        data = envelope.get("data") if isinstance(envelope, dict) else envelope
        results = (data or {}).get("results") if isinstance(data, dict) else data
        repos = list(results or [])

        if include_tags:
            for repo in repos:
                rname = repo.get("name")
                if not rname:
                    continue
                try:
                    tenv = client.get_repository_tags(
                        namespace=namespace, repository=rname
                    )
                    tdata = tenv.get("data") if isinstance(tenv, dict) else tenv
                    tags = (
                        (tdata or {}).get("results")
                        if isinstance(tdata, dict)
                        else tdata
                    )
                    repo["tags"] = list(tags or [])
                except Exception:  # noqa: BLE001 — best-effort tag enrichment
                    repo["tags"] = []

        result = ingest_repositories(repos, namespace=namespace)
        return {"listed": len(repos), "ingested": result}

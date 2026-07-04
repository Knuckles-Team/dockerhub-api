"""MCP tool for Docker Scout (CVE / SBOM / policy intelligence).

CONCEPT:DH-OS.audit.action-routed-mcp-surface — action-routed MCP surface.
CONCEPT:DH-OS.identity.docker-scout-client-cve — Docker Scout client.
"""

from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.dependencies import Depends
from pydantic import Field

from dockerhub_api.mcp import (
    get_scout_client,
    parse_params,
    redact_secrets,
    run_action,
)


def register_scout_tools(mcp: FastMCP):
    @mcp.tool(tags={"scout"})
    async def hub_scout(
        action: str = Field(
            description=(
                "Action to perform. Must be one of: 'summary', 'cves', "
                "'vulnerabilities', 'sbom', 'compare', 'policies', "
                "'policy_evaluation'"
            )
        ),
        params_json: str = Field(
            default="{}", description="JSON string of parameters to pass to the action."
        ),
        client=Depends(get_scout_client),
        ctx: Context | None = Field(
            default=None, description="MCP context for progress reporting"
        ),
    ) -> Any:
        """Docker Scout image intelligence (``api.scout.docker.com``):
        vulnerability/CVE listings, image summaries, SBOM retrieval, image
        comparison, and organization policy evaluation. Authenticated with the
        Hub credentials; most actions require a Scout-enabled organization.
        """
        if ctx:
            await ctx.info("Executing tool...")
        try:
            kwargs = parse_params(params_json)
        except Exception as e:
            return {"error": f"Invalid params_json: {e}"}

        handlers = {
            "summary": client.get_image_summary,
            "cves": client.get_cves,
            "vulnerabilities": client.list_vulnerabilities,
            "sbom": client.get_sbom,
            "compare": client.compare,
            "policies": client.list_policies,
            "policy_evaluation": client.get_policy_evaluation,
        }
        return redact_secrets(run_action(handlers, action, kwargs))

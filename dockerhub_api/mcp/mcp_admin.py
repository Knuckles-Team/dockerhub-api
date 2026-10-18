"""MCP tool for Docker Hub client telemetry and identity introspection.

CONCEPT:DH-OS.audit.action-routed-mcp-surface — typed per-action MCP surface.
CONCEPT:DH-OS.governance.rate-limit-telemetry-every — rate-limit telemetry.
"""

from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.dependencies import Depends
from pydantic import Field

from dockerhub_api.mcp import get_hub_client, redact_secrets


def register_admin_tools(mcp: FastMCP):
    @mcp.tool(
        tags={"admin"},
        annotations={
            "readOnlyHint": True,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def hub_admin_rate_limit(
        client=Depends(get_hub_client),
        ctx: Context | None = Field(
            default=None, description="MCP context for progress reporting"
        ),
    ) -> dict[str, Any]:
        """Return the latest X-RateLimit-* snapshot observed by the client."""
        if ctx:
            await ctx.info("Reading the rate-limit snapshot...")
        return redact_secrets(client.get_rate_limit())

    @mcp.tool(
        tags={"admin"},
        annotations={
            "readOnlyHint": True,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def hub_admin_whoami(
        client=Depends(get_hub_client),
        ctx: Context | None = Field(
            default=None, description="MCP context for progress reporting"
        ),
    ) -> dict[str, Any]:
        """Introspect the active credential locally (decoded JWT claims, no network call)."""
        if ctx:
            await ctx.info("Introspecting the active credential...")
        return redact_secrets(client.whoami())

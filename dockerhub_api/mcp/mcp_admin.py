"""MCP tool for Docker Hub client telemetry and identity introspection.

CONCEPT:DH-OS.audit.action-routed-mcp-surface — action-routed MCP surface.
CONCEPT:DH-OS.governance.rate-limit-telemetry-every — rate-limit telemetry.
"""

from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.dependencies import Depends
from pydantic import Field

from dockerhub_api.mcp import get_hub_client, parse_params, redact_secrets, run_action


def register_admin_tools(mcp: FastMCP):
    @mcp.tool(tags={"admin"})
    async def hub_admin(
        action: str = Field(
            description="Action to perform. Must be one of: 'rate_limit', 'whoami'"
        ),
        params_json: str = Field(
            default="{}", description="JSON string of parameters to pass to the action."
        ),
        client=Depends(get_hub_client),
        ctx: Context | None = Field(
            default=None, description="MCP context for progress reporting"
        ),
    ) -> Any:
        """Client diagnostics: 'rate_limit' returns the latest
        X-RateLimit-* snapshot observed by the client; 'whoami' introspects
        the active credential locally (decoded JWT claims, no network call).
        """
        if ctx:
            await ctx.info("Executing tool...")
        try:
            kwargs = parse_params(params_json)
        except Exception as e:
            return {"error": "Operation failed"}

        handlers = {
            "rate_limit": client.get_rate_limit,
            "whoami": client.whoami,
        }
        return redact_secrets(run_action(handlers, action, kwargs))

"""MCP tool for Docker Hub audit logs.

CONCEPT:DH-OS.audit.action-routed-mcp-surface — action-routed MCP surface.
"""

from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.dependencies import Depends
from pydantic import Field

from dockerhub_api.mcp import get_hub_client, parse_params, redact_secrets, run_action


def register_audit_tools(mcp: FastMCP):
    @mcp.tool(tags={"audit"})
    async def hub_audit(
        action: str = Field(
            description="Action to perform. Must be one of: 'logs', 'actions'"
        ),
        params_json: str = Field(
            default="{}", description="JSON string of parameters to pass to the action."
        ),
        client=Depends(get_hub_client),
        ctx: Context | None = Field(
            default=None, description="MCP context for progress reporting"
        ),
    ) -> Any:
        """Read a Docker Hub account's audit trail: 'logs' lists events
        (filters: action, name, actor, from_date, to_date, page, page_size),
        'actions' lists the available action names.
        """
        if ctx:
            await ctx.info("Executing tool...")
        try:
            kwargs = parse_params(params_json)
        except Exception as e:
            return {"error": f"Invalid params_json: {e}"}

        handlers = {
            "logs": client.get_audit_logs,
            "actions": client.get_audit_log_actions,
        }
        return redact_secrets(run_action(handlers, action, kwargs))

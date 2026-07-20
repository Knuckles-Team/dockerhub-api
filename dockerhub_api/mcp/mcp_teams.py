"""MCP tool for Docker Hub groups (teams) and their membership.

CONCEPT:DH-OS.audit.action-routed-mcp-surface — action-routed MCP surface.
"""

from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.dependencies import Depends
from pydantic import Field

from dockerhub_api.mcp import get_hub_client, parse_params, redact_secrets, run_action


def register_teams_tools(mcp: FastMCP):
    @mcp.tool(tags={"teams"})
    async def hub_teams(
        action: str = Field(
            description=(
                "Action to perform. Must be one of: 'list', 'create', 'get', "
                "'update', 'patch', 'delete', 'list_members', 'add_member', "
                "'remove_member'"
            )
        ),
        params_json: str = Field(
            default="{}", description="JSON string of parameters to pass to the action."
        ),
        client=Depends(get_hub_client),
        ctx: Context | None = Field(
            default=None, description="MCP context for progress reporting"
        ),
    ) -> Any:
        """Manage Docker Hub organization groups (teams) and their members.
        Group deletion and member removal require
        DOCKERHUB_ALLOW_DESTRUCTIVE=True.
        """
        if ctx:
            await ctx.info("Executing tool...")
        try:
            kwargs = parse_params(params_json)
        except Exception as e:
            return {"error": "Operation failed"}

        handlers = {
            "list": client.get_groups,
            "create": client.create_group,
            "get": client.get_group,
            "update": client.update_group,
            "patch": client.patch_group,
            "delete": client.delete_group,
            "list_members": client.get_group_members,
            "add_member": client.add_group_member,
            "remove_member": client.remove_group_member,
        }
        return redact_secrets(run_action(handlers, action, kwargs))

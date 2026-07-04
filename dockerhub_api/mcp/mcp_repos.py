"""MCP tool for Docker Hub repositories and tags.

CONCEPT:DH-OS.audit.action-routed-mcp-surface — action-routed MCP surface.
"""

from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.dependencies import Depends
from pydantic import Field

from dockerhub_api.mcp import get_hub_client, parse_params, redact_secrets, run_action


def register_repos_tools(mcp: FastMCP):
    @mcp.tool(tags={"repositories"})
    async def hub_repos(
        action: str = Field(
            description=(
                "Action to perform. Must be one of: 'list', 'create', 'get', "
                "'check', 'list_tags', 'check_tags', 'get_tag', 'check_tag', "
                "'set_immutable_tags', 'verify_immutable_tags', 'assign_group'"
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
        """Manage Docker Hub repositories: list/create/inspect repositories,
        browse tags, configure and verify immutable tags, and grant teams
        repository permissions. Repository creation is the primary release
        provisioning path and is allowed by default.
        """
        if ctx:
            await ctx.info("Executing tool...")
        try:
            kwargs = parse_params(params_json)
        except Exception as e:
            return {"error": f"Invalid params_json: {e}"}

        handlers = {
            "list": client.get_repositories,
            "create": client.create_repository,
            "get": client.get_repository,
            "check": client.check_repository,
            "list_tags": client.get_repository_tags,
            "check_tags": client.check_repository_tags,
            "get_tag": client.get_repository_tag,
            "check_tag": client.check_repository_tag,
            "set_immutable_tags": client.update_immutable_tags,
            "verify_immutable_tags": client.verify_immutable_tags,
            "assign_group": client.assign_repository_group,
        }
        return redact_secrets(run_action(handlers, action, kwargs))

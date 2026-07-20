"""MCP tool for Docker Hub SCIM 2.0 provisioning.

CONCEPT:DH-OS.audit.action-routed-mcp-surface — action-routed MCP surface.
CONCEPT:DH-OS.governance.scim-provisioning-all-requests — SCIM provisioning.
"""

from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.dependencies import Depends
from pydantic import Field

from dockerhub_api.mcp import get_hub_client, parse_params, redact_secrets, run_action


def register_scim_tools(mcp: FastMCP):
    @mcp.tool(tags={"scim"})
    async def hub_scim(
        action: str = Field(
            description=(
                "Action to perform. Must be one of: 'service_provider_config', "
                "'resource_types', 'resource_type', 'schemas', 'schema', "
                "'list_users', 'get_user', 'create_user', 'update_user'"
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
        """Docker Hub SCIM 2.0: service discovery (ServiceProviderConfig,
        ResourceTypes, Schemas) and user provisioning (list with
        startIndex/count/filter/sortBy/sortOrder, get, create, replace).
        """
        if ctx:
            await ctx.info("Executing tool...")
        try:
            kwargs = parse_params(params_json)
        except Exception as e:
            return {"error": "Operation failed"}

        handlers = {
            "service_provider_config": client.get_scim_service_provider_config,
            "resource_types": client.get_scim_resource_types,
            "resource_type": client.get_scim_resource_type,
            "schemas": client.get_scim_schemas,
            "schema": client.get_scim_schema,
            "list_users": client.get_scim_users,
            "get_user": client.get_scim_user,
            "create_user": client.create_scim_user,
            "update_user": client.replace_scim_user,
        }
        return redact_secrets(run_action(handlers, action, kwargs))

"""MCP tool for Docker Hub organization members, settings, and invites.

CONCEPT:DH-OS.audit.action-routed-mcp-surface — action-routed MCP surface.
"""

from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.dependencies import Depends
from pydantic import Field

from dockerhub_api.mcp import get_hub_client, parse_params, redact_secrets, run_action


def register_org_tools(mcp: FastMCP):
    @mcp.tool(tags={"org"})
    async def hub_org(
        action: str = Field(
            description=(
                "Action to perform. Must be one of: 'get_settings', "
                "'update_settings', 'list_members', 'export_members', "
                "'update_member', 'remove_member', 'list_invites', "
                "'delete_invite', 'resend_invite', 'bulk_invite'"
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
        """Manage a Docker Hub organization: settings (restricted images),
        member roster and roles, CSV export, and invites (single, resend,
        bulk with dry_run). Member removal, invite deletion, and settings
        writes require DOCKERHUB_ALLOW_DESTRUCTIVE=True.
        """
        if ctx:
            await ctx.info("Executing tool...")
        try:
            kwargs = parse_params(params_json)
        except Exception as e:
            return {"error": f"Invalid params_json: {e}"}

        handlers = {
            "get_settings": client.get_org_settings,
            "update_settings": client.update_org_settings,
            "list_members": client.get_org_members,
            "export_members": client.export_org_members,
            "update_member": client.update_org_member,
            "remove_member": client.remove_org_member,
            "list_invites": client.get_org_invites,
            "delete_invite": client.delete_invite,
            "resend_invite": client.resend_invite,
            "bulk_invite": client.bulk_invite,
        }
        return redact_secrets(run_action(handlers, action, kwargs))

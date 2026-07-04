"""MCP tool for Docker Hub auth and token lifecycle.

CONCEPT:DH-OS.audit.action-routed-mcp-surface — action-routed MCP surface.
"""

from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.dependencies import Depends
from pydantic import Field

from dockerhub_api.mcp import get_hub_client, parse_params, redact_secrets, run_action


def register_auth_tools(mcp: FastMCP):
    @mcp.tool(tags={"auth"})
    async def hub_auth(
        action: str = Field(
            description=(
                "Action to perform. Must be one of: 'create_token', 'login' "
                "(deprecated), 'two_factor_login', 'list_pats', 'create_pat', "
                "'get_pat', 'update_pat', 'delete_pat', 'list_oats', "
                "'create_oat', 'get_oat', 'update_oat', 'delete_oat'"
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
        """Manage Docker Hub authentication, personal access tokens (PATs),
        and organization access tokens (OATs).

        Bearer JWTs are minted/cached client-side and redacted from results.
        Plaintext PAT/OAT values appear exactly once, on creation. Token
        deletion requires DOCKERHUB_ALLOW_DESTRUCTIVE=True.
        """
        if ctx:
            await ctx.info("Executing tool...")
        try:
            kwargs = parse_params(params_json)
        except Exception as e:
            return {"error": f"Invalid params_json: {e}"}

        handlers = {
            "create_token": client.create_auth_token,
            "login": client.login,
            "two_factor_login": client.two_factor_login,
            "list_pats": client.get_access_tokens,
            "create_pat": client.create_access_token,
            "get_pat": client.get_access_token,
            "update_pat": client.update_access_token,
            "delete_pat": client.delete_access_token,
            "list_oats": client.get_org_access_tokens,
            "create_oat": client.create_org_access_token,
            "get_oat": client.get_org_access_token,
            "update_oat": client.update_org_access_token,
            "delete_oat": client.delete_org_access_token,
        }
        result = run_action(handlers, action, kwargs)
        # Plaintext tokens are shown exactly once — on creation.
        allow_keys = {"token"} if action in ("create_pat", "create_oat") else set()
        return redact_secrets(result, allow_keys=allow_keys)

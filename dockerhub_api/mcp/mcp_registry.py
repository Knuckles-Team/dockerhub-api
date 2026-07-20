"""MCP tool for the Registry HTTP API v2.

CONCEPT:DH-OS.audit.action-routed-mcp-surface — action-routed MCP surface.
CONCEPT:DH-OS.identity.registry-v2-scoped-token — Registry v2 client.
CONCEPT:DH-OS.governance.registry-v2-mcp-tool — Registry v2 MCP tool (``hub_registry``).
CONCEPT:DH-OS.governance.oci-referrers-attestation-discovery — OCI Referrers / attestation discovery.
CONCEPT:DH-OS.governance.chunked-blob-push-upload — chunked blob push.
"""

from typing import Any

from fastmcp import Context, FastMCP
from fastmcp.dependencies import Depends
from pydantic import Field

from dockerhub_api.mcp import (
    get_registry_client,
    parse_params,
    redact_secrets,
    run_action,
)


def register_registry_tools(mcp: FastMCP):
    @mcp.tool(tags={"registry"})
    async def hub_registry(
        action: str = Field(
            description=(
                "Action to perform. Must be one of: 'api_version', 'list_tags', "
                "'get_manifest', 'check_manifest', 'resolve_digest', "
                "'list_platforms', 'get_config', 'inspect', 'get_blob', "
                "'check_blob', 'list_referrers', 'delete_manifest', 'delete_blob', "
                "'start_upload', 'upload_chunk', 'complete_upload', 'mount_blob', "
                "'put_manifest'"
            )
        ),
        params_json: str = Field(
            default="{}", description="JSON string of parameters to pass to the action."
        ),
        client=Depends(get_registry_client),
        ctx: Context | None = Field(
            default=None, description="MCP context for progress reporting"
        ),
    ) -> Any:
        """Docker Registry v2 image operations (``registry-1.docker.io``):
        list tags, read/resolve manifests and digests, inspect multi-arch
        platforms, fetch image config and blobs, discover OCI referrers
        (SBOM/provenance attestations), and — gated by
        DOCKERHUB_ALLOW_DESTRUCTIVE — delete manifests/blobs and push via the
        chunked blob-upload protocol. Single-segment repos (e.g. 'nginx') are
        normalized to their 'library/' official path.
        """
        if ctx:
            await ctx.info("Executing tool...")
        try:
            kwargs = parse_params(params_json)
        except Exception as e:
            return {"error": "Operation failed"}

        handlers = {
            "api_version": client.api_version,
            "list_tags": client.list_tags,
            "get_manifest": client.get_manifest,
            "check_manifest": client.check_manifest,
            "resolve_digest": client.resolve_digest,
            "list_platforms": client.list_platforms,
            "get_config": client.get_config,
            "inspect": client.inspect,
            "get_blob": client.get_blob,
            "check_blob": client.check_blob,
            "list_referrers": client.list_referrers,
            "delete_manifest": client.delete_manifest,
            "delete_blob": client.delete_blob,
            "start_upload": client.start_upload,
            "upload_chunk": client.upload_chunk,
            "complete_upload": client.complete_upload,
            "mount_blob": client.mount_blob,
            "put_manifest": client.put_manifest,
        }
        return redact_secrets(run_action(handlers, action, kwargs))

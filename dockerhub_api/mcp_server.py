#!/usr/bin/python
"""Docker Hub MCP server entry point.

CONCEPT:HUB-1.4 — action-routed MCP surface. Registers the consolidated,
togglable tool modules (hub_auth, hub_repos, hub_org, hub_teams, hub_audit,
hub_scim, hub_admin, hub_registry, hub_scout) on an agent-utilities FastMCP
server.
"""

import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore")

warnings.filterwarnings("ignore", message=".*urllib3.*or chardet.*")
warnings.filterwarnings("ignore", message=".*urllib3.*or charset_normalizer.*")

import logging
import os
import sys
from typing import Any

from agent_utilities.mcp_utilities import (
    create_mcp_server,
    load_config,
    register_tool_surface,
)
from fastmcp.utilities.logging import get_logger

from dockerhub_api.api_client import Api
from dockerhub_api.auth import get_client
from dockerhub_api.mcp import (
    register_admin_tools,  # noqa: F401
    register_audit_tools,  # noqa: F401
    register_auth_tools,  # noqa: F401
    register_org_tools,  # noqa: F401
    register_registry_tools,  # noqa: F401
    register_repos_tools,  # noqa: F401
    register_scim_tools,  # noqa: F401
    register_scout_tools,  # noqa: F401
    register_teams_tools,  # noqa: F401
)

__version__ = "1.0.1"
print(f"Docker Hub MCP v{__version__}", file=sys.stderr)

logger = get_logger(name="mcp_server")
logger.setLevel(logging.DEBUG)


def get_mcp_instance() -> tuple[Any, Any, Any, Any]:
    """Initialize and return the Docker Hub MCP instance, args, and middlewares."""
    load_config()
    os.environ["FASTMCP_LOG_LEVEL"] = "ERROR"
    os.environ["TERM"] = "dumb"
    os.environ["NO_COLOR"] = "1"

    args, mcp, middlewares = create_mcp_server(
        name="DockerHub",
        version=__version__,
        instructions=(
            "Docker Hub API MCP Server - Manage repositories, tags, access "
            "tokens, organizations, teams, audit logs, and SCIM provisioning; "
            "plus Registry v2 image operations (manifests, blobs, digests, "
            "multi-arch inspect, OCI referrers, gated push/delete) and Docker "
            "Scout CVE/SBOM/policy intelligence."
        ),
    )

    registered_tags = register_tool_surface(
        mcp,
        client_cls=Api,
        get_client=get_client,
        service="dockerhub-api",
        tools_module=sys.modules[__name__],
    )

    for mw in middlewares:
        mcp.add_middleware(mw)

    return mcp, args, middlewares, registered_tags


def mcp_server() -> None:
    mcp, args, middlewares, registered_tags = get_mcp_instance()
    print(f"{'dockerhub-api'} MCP v{__version__}", file=sys.stderr)
    print("\nStarting MCP Server", file=sys.stderr)
    print(f"  Transport: {args.transport.upper()}", file=sys.stderr)
    print(f"  Auth: {args.auth_type}", file=sys.stderr)
    print(f"  Dynamic Tags Loaded: {len(set(registered_tags))}", file=sys.stderr)

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "streamable-http":
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    elif args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        logger.error("Invalid transport", extra={"transport": args.transport})
        sys.exit(1)


if __name__ == "__main__":
    mcp_server()

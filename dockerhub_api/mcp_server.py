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

from agent_utilities.base_utilities import to_boolean
from agent_utilities.mcp_utilities import create_mcp_server
from dotenv import find_dotenv, load_dotenv
from fastmcp.utilities.logging import get_logger

from dockerhub_api.mcp import (
    register_admin_tools,
    register_audit_tools,
    register_auth_tools,
    register_org_tools,
    register_registry_tools,
    register_repos_tools,
    register_scim_tools,
    register_scout_tools,
    register_teams_tools,
)

__version__ = "0.4.0"
print(f"Docker Hub MCP v{__version__}", file=sys.stderr)

logger = get_logger(name="mcp_server")
logger.setLevel(logging.DEBUG)

DEFAULT_DOCKERHUB_SSL_VERIFY = to_boolean(
    string=os.getenv("DOCKERHUB_SSL_VERIFY", "True")
)
DEFAULT_DOCKERHUB_URL = os.getenv("DOCKERHUB_URL", "https://hub.docker.com")
DEFAULT_DOCKERHUB_TOKEN = os.getenv("DOCKERHUB_TOKEN", None)

#: (env toggle, register function) — every consolidated tool module.
TOOL_REGISTRY = (
    ("AUTHTOOL", register_auth_tools),
    ("REPOSTOOL", register_repos_tools),
    ("ORGTOOL", register_org_tools),
    ("TEAMSTOOL", register_teams_tools),
    ("AUDITTOOL", register_audit_tools),
    ("SCIMTOOL", register_scim_tools),
    ("ADMINTOOL", register_admin_tools),
    ("REGISTRYTOOL", register_registry_tools),
    ("SCOUTTOOL", register_scout_tools),
)


def get_mcp_instance() -> tuple[Any, Any, Any, Any]:
    """Initialize and return the Docker Hub MCP instance, args, and middlewares."""
    load_dotenv(find_dotenv())
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

    registered_tags: list[str] = []
    for toggle, register in TOOL_REGISTRY:
        if to_boolean(string=os.getenv(toggle, "True")):
            register(mcp)
            registered_tags.append(toggle)

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

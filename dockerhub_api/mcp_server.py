#!/usr/bin/python
"""Docker Hub MCP server entry point.

CONCEPT:DH-OS.audit.action-routed-mcp-surface — action-routed MCP surface. Registers the consolidated,
togglable tool modules (hub_auth, hub_repos, hub_org, hub_teams, hub_audit,
hub_scim, hub_admin, hub_registry, hub_scout) on an agent-connector-sdk FastMCP
server.
"""

import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore")

warnings.filterwarnings("ignore", message=".*urllib3.*or chardet.*")
warnings.filterwarnings("ignore", message=".*urllib3.*or charset_normalizer.*")


from dockerhub_api.mcp import (
    register_admin_tools,
    register_audit_tools,
    register_auth_tools,
    register_kg_tools,
    register_org_tools,
    register_registry_tools,
    register_repos_tools,
    register_scim_tools,
    register_scout_tools,
    register_teams_tools,
)

# SDK discovery registers the register_<tag>_tools functions bound in this module.
__all__ = [
    "register_admin_tools",
    "register_audit_tools",
    "register_auth_tools",
    "register_kg_tools",
    "register_org_tools",
    "register_registry_tools",
    "register_repos_tools",
    "register_scim_tools",
    "register_scout_tools",
    "register_teams_tools",
]

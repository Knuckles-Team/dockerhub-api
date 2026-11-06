#!/usr/bin/python
"""Docker Hub MCP server entry point.

CONCEPT:DH-OS.audit.action-routed-mcp-surface — typed MCP surface. Registers the admin and ingest tools;
the per-operation tools are derived from the client methods by the connector.
"""

import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore")

warnings.filterwarnings("ignore", message=".*urllib3.*or chardet.*")
warnings.filterwarnings("ignore", message=".*urllib3.*or charset_normalizer.*")


from dockerhub_api.mcp import (
    register_admin_tools,
    register_kg_tools,
)

# SDK discovery registers the register_<tag>_tools functions bound in this module.
__all__ = [
    "register_admin_tools",
    "register_kg_tools",
]

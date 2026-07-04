"""MCP tool registration modules for dockerhub-api.

CONCEPT:DH-OS.audit.action-routed-mcp-surface — action-routed MCP surface. Each module registers one
consolidated, action-routed tool; this package provides the shared client
resolution, parameter parsing, secret redaction, and error-envelope helpers.
"""

import json
from typing import Any

from agent_utilities.core.exceptions import (
    ApiError,
    AuthError,
    MissingParameterError,
    ParameterError,
    UnauthorizedError,
)

from dockerhub_api.api.api_client_base import DestructiveOperationError

#: Keys whose values are always masked in MCP tool results.
SECRET_KEYS = {"secret", "password", "access_token", "refresh_token", "jwt"}
REDACTED = "***redacted***"


def get_hub_client():
    """Resolve the Docker Hub client late so tests/deployments can rebind
    ``dockerhub_api.auth.get_client``."""
    from dockerhub_api.auth import get_client

    return get_client()


def get_registry_client():
    """Resolve the Registry v2 client late (rebindable in tests/deployments)."""
    from dockerhub_api.auth import get_registry_client as _factory

    return _factory()


def get_scout_client():
    """Resolve the Docker Scout client late (rebindable in tests/deployments)."""
    from dockerhub_api.auth import get_scout_client as _factory

    return _factory()


def parse_params(params_json: str) -> dict[str, Any]:
    """Parse the ``params_json`` tool argument, dropping ``None`` values."""
    kwargs = json.loads(params_json) if params_json else {}
    if not isinstance(kwargs, dict):
        raise ValueError("params_json must decode to a JSON object")
    return {k: v for k, v in kwargs.items() if v is not None}


def redact_secrets(data: Any, allow_keys: set[str] | None = None) -> Any:
    """Recursively mask secret-bearing fields in a tool result.

    ``allow_keys`` whitelists keys that must stay visible for this one call
    (e.g. the plaintext ``token`` returned exactly once on PAT creation).
    """
    allow = allow_keys or set()
    if isinstance(data, dict):
        return {
            key: (
                REDACTED
                if key in SECRET_KEYS and key not in allow and value
                else redact_secrets(value, allow)
            )
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [redact_secrets(item, allow) for item in data]
    return data


def error_envelope(error: Exception) -> dict[str, Any]:
    """Map a client exception to the MCP error envelope."""
    return {"error": {"type": type(error).__name__, "message": str(error)}}


HANDLED_ERRORS = (
    ApiError,
    AuthError,
    UnauthorizedError,
    ParameterError,
    MissingParameterError,
    DestructiveOperationError,
    ValueError,
)


def run_action(handlers: dict, action: str, kwargs: dict[str, Any]) -> Any:
    """Dispatch ``action`` to its handler, mapping errors to the envelope."""
    handler = handlers.get(action)
    if handler is None:
        return {
            "error": {
                "type": "UnknownAction",
                "message": f"Unknown action: {action!r}. "
                f"Valid actions: {sorted(handlers)}",
            }
        }
    try:
        return handler(**kwargs)
    except HANDLED_ERRORS as error:
        return error_envelope(error)


from dockerhub_api.mcp.mcp_admin import register_admin_tools
from dockerhub_api.mcp.mcp_audit import register_audit_tools
from dockerhub_api.mcp.mcp_auth import register_auth_tools
from dockerhub_api.mcp.mcp_org import register_org_tools
from dockerhub_api.mcp.mcp_registry import register_registry_tools
from dockerhub_api.mcp.mcp_repos import register_repos_tools
from dockerhub_api.mcp.mcp_scim import register_scim_tools
from dockerhub_api.mcp.mcp_scout import register_scout_tools
from dockerhub_api.mcp.mcp_teams import register_teams_tools

__all__ = [
    "HANDLED_ERRORS",
    "REDACTED",
    "SECRET_KEYS",
    "error_envelope",
    "get_hub_client",
    "get_registry_client",
    "get_scout_client",
    "parse_params",
    "redact_secrets",
    "register_admin_tools",
    "register_audit_tools",
    "register_auth_tools",
    "register_org_tools",
    "register_registry_tools",
    "register_repos_tools",
    "register_scim_tools",
    "register_scout_tools",
    "register_teams_tools",
    "run_action",
]

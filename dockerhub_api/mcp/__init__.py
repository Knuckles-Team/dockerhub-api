"""MCP tool registration modules for dockerhub-api.

CONCEPT:DH-OS.audit.action-routed-mcp-surface — typed MCP surface. The per-operation tools come from the
client methods; this package provides the shared client
resolution, parameter parsing, secret redaction, and error-envelope helpers.
"""

from typing import Any

from scion_sdk.exceptions import (
    ApiError,
    AuthError,
    MissingParameterError,
    ParameterError,
    UnauthorizedError,
)

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
    return {"error": {"type": type(error).__name__, "message": type(error).__name__}}


HANDLED_ERRORS = (
    ApiError,
    AuthError,
    UnauthorizedError,
    ParameterError,
    MissingParameterError,
    ValueError,
)


from dockerhub_api.mcp.mcp_admin import register_admin_tools
from dockerhub_api.mcp.mcp_kg import register_kg_tools

__all__ = [
    "HANDLED_ERRORS",
    "REDACTED",
    "SECRET_KEYS",
    "error_envelope",
    "get_hub_client",
    "get_registry_client",
    "get_scout_client",
    "redact_secrets",
    "register_admin_tools",
    "register_kg_tools",
]

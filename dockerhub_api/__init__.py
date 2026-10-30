#!/usr/bin/env python

import importlib
import inspect
from typing import Any

__all__: list[str] = []

CORE_MODULES: list[str] = [
    "dockerhub_api.dockerhub_input_models",
    "dockerhub_api.dockerhub_response_models",
    "dockerhub_api.api_client",
    "dockerhub_api.auth",
]

OPTIONAL_MODULES = {
    "dockerhub_api.mcp_server": "mcp",
}


def _expose_members(module):
    """Expose public classes and functions from a module into globals and __all__."""
    for name, obj in inspect.getmembers(module):
        if (inspect.isclass(obj) or inspect.isfunction(obj)) and not name.startswith(
            "_"
        ):
            globals()[name] = obj
            if name not in __all__:
                __all__.append(name)


# Eagerly import core modules (keeps API wrappers fast & light)
for module_name in CORE_MODULES:
    if module_name:
        module = importlib.import_module(module_name)
        _expose_members(module)

# Dynamic/lazy loading of optional modules (agent_server, mcp_server)
_loaded_optional_modules: dict[str, Any] = {}


def _import_module_safely(module_name: str):
    """Try to import a module and return it, or None if not available."""
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None


_AVAILABILITY_FLAG_MARKERS = {
    "_MCP_AVAILABLE": "mcp_server",
}
_NOT_AN_AVAILABILITY_FLAG = object()
_NAME_NOT_FOUND = object()


def _resolve_availability_flag(name: str) -> Any:
    """Return the live availability bool for a ``_*_AVAILABLE`` flag name.

    Returns ``_NOT_AN_AVAILABILITY_FLAG`` when ``name`` is not one of the
    recognized flags, so callers can distinguish "not a flag" from "flag
    resolved to False".
    """
    marker = _AVAILABILITY_FLAG_MARKERS.get(name)
    if marker is None:
        return _NOT_AN_AVAILABILITY_FLAG
    module_key = next((k for k in OPTIONAL_MODULES if marker in k), None)
    if module_key is None:
        return False
    return _import_module_safely(module_key) is not None


def _resolve_from_optional_modules(name: str) -> Any:
    """Lazily import each optional module and return its ``name`` attribute."""
    for module_name in OPTIONAL_MODULES:
        module = _loaded_optional_modules.get(module_name)
        if module is None:
            module = _import_module_safely(module_name)
            if module is not None:
                _loaded_optional_modules[module_name] = module
                _expose_members(module)
        if module is not None and hasattr(module, name):
            return getattr(module, name)
    return _NAME_NOT_FOUND


def __getattr__(name: str) -> Any:
    flag = _resolve_availability_flag(name)
    if flag is not _NOT_AN_AVAILABILITY_FLAG:
        return flag

    value = _resolve_from_optional_modules(name)
    if value is not _NAME_NOT_FOUND:
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + __all__)


from scion_sdk.connector import Connector

from dockerhub_api.api.api_client_registry import RegistryApi
from dockerhub_api.api.api_client_scout import ScoutApi
from dockerhub_api.api_client import Api
from dockerhub_api.mcp import (
    get_hub_client,
    get_registry_client,
    get_scout_client,
    redact_secrets,
)

connector = Connector(
    api=Api,
    get_client=get_hub_client,
    tools="dockerhub_api.mcp_server",
    instructions="Docker Hub API MCP Server - Manage repositories, tags, access tokens, organizations, teams, audit logs, and SCIM provisioning; plus Registry v2 image operations (manifests, blobs, digests, multi-arch inspect, OCI referrers, gated push/delete) and Docker Scout CVE/SBOM/policy intelligence.",
    verbose_targets=(
        {
            "client_cls": RegistryApi,
            "get_client": get_registry_client,
            "prefix": "dockerhub_registry",
        },
        {
            "client_cls": ScoutApi,
            "get_client": get_scout_client,
            "prefix": "dockerhub_scout",
        },
    ),
    result_coercer=redact_secrets,
)

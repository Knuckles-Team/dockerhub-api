"""Package import + dynamic ``__all__`` exposure (CONCEPT:DH-OS.audit.core-wrapper-api-is)."""

import importlib


def test_package_imports():
    module = importlib.import_module("dockerhub_api")
    assert hasattr(module, "__all__")


def test_core_symbols_exposed():
    module = importlib.import_module("dockerhub_api")
    for symbol in ("Api", "get_client", "TokenManager"):
        assert symbol in module.__all__
        assert hasattr(module, symbol)


def test_availability_flags_are_booleans():
    module = importlib.import_module("dockerhub_api")
    assert isinstance(module._MCP_AVAILABLE, bool)
    assert isinstance(module._AGENT_AVAILABLE, bool)

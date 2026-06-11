"""Package import / entry-point sanity."""

import subprocess
import sys


def test_package_imports():
    import dockerhub_api

    assert hasattr(dockerhub_api, "Api")
    assert hasattr(dockerhub_api, "TokenManager")
    assert callable(dockerhub_api.get_client)


def test_optional_module_flags():
    import dockerhub_api

    assert dockerhub_api._MCP_AVAILABLE is True
    assert dockerhub_api._AGENT_AVAILABLE is True


def test_mcp_server_help():
    result = subprocess.run(
        [sys.executable, "-m", "dockerhub_api.mcp_server", "--help"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0


def test_agent_server_help():
    result = subprocess.run(
        [sys.executable, "-m", "dockerhub_api.agent_server", "--help"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0


import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]






def test_packaged_mcp_config_is_valid_json():
    config = json.loads((REPO_ROOT / "dockerhub_api" / "mcp_config.json").read_text())
    assert "mcpServers" in config


def test_root_mcp_config_registers_server():
    config = json.loads((REPO_ROOT / "mcp_config.json").read_text())
    assert "dockerhub-api" in config["mcpServers"]

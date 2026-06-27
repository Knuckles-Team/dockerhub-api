"""A2A metadata validation (a2a.json, main_agent.json, mcp_config.json)."""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_a2a_manifest_shape():
    manifest = json.loads((REPO_ROOT / "a2a.json").read_text())
    assert manifest["name"] == "dockerhub-api-agent"
    assert manifest["type"] == "agent"
    assert manifest["capabilities"]
    assert manifest["tools"]


def test_main_agent_prompt():
    prompt = json.loads((REPO_ROOT / "dockerhub_api" / "main_agent.json").read_text())
    assert prompt["task"] == "main-agent"
    assert "Docker Hub" in prompt["instructions"]["core_directive"]


def test_packaged_mcp_config_is_valid_json():
    config = json.loads((REPO_ROOT / "dockerhub_api" / "mcp_config.json").read_text())
    assert "mcpServers" in config


def test_root_mcp_config_registers_server():
    config = json.loads((REPO_ROOT / "mcp_config.json").read_text())
    assert "dockerhub-api" in config["mcpServers"]

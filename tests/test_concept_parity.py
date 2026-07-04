"""Every CONCEPT:DH-OS.governance.hub-x marker in code must be registered in docs/concepts.md."""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MARKER = re.compile(r"CONCEPT:DH-OS.governance.hub\.\d+")


def collect_code_markers() -> set[str]:
    markers: set[str] = set()
    for path in (REPO / "dockerhub_api").rglob("*.py"):
        markers.update(MARKER.findall(path.read_text(encoding="utf-8")))
    return markers


def test_code_markers_are_registered_in_docs():
    registry = (REPO / "docs" / "concepts.md").read_text(encoding="utf-8")
    documented = set(MARKER.findall(registry))
    in_code = collect_code_markers()
    assert in_code, "Expected CONCEPT:DH-OS.governance.hub-x markers in dockerhub_api/"
    assert in_code <= documented, f"Unregistered concepts: {in_code - documented}"


def test_root_concept_exists_in_code_and_docs():
    registry = (REPO / "docs" / "concepts.md").read_text(encoding="utf-8")
    assert "CONCEPT:DH-OS.audit.core-wrapper-api-is" in registry
    assert "CONCEPT:DH-OS.audit.core-wrapper-api-is" in collect_code_markers()


def test_registry_carries_eco_bridge_and_prefix():
    registry = (REPO / "docs" / "concepts.md").read_text(encoding="utf-8")
    assert "AU-ECO.messaging.native-backend-abstraction" in registry
    assert "CONCEPT:DH-OS.governance.hub-x" in registry

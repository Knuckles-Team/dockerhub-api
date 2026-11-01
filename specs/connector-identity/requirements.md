# CONN-DOCKERHUB-API-CONNECTOR-IDENTITY — Requirements

Governing spec: [spec.md](spec.md).

Each row is one requirement. A row names the file it touches and the test that proves it. The generator sets each row's state in `status.json`.

| ID | Requirement | Acceptance |
|---|---|---|
| `CONN-DOCKERHUB-API-CONNECTOR-IDENTITY-R001` | **Fleet name.** `pyproject.toml` declares `dockerhub-mcp` as the single `scion_sdk.connector` entry point. The content pack, the manifest `connector`, the fingerprints and the ingest binding all carry `dockerhub-mcp`. Proving test: `tests/test_fleet_name.py::test_connector_name_is_the_fleet_name`. Caller chain: console_script dockerhub-mcp (scion_sdk.cli:serve L18) -> installed_connectors -> dockerhub_api/__init__.py::connector (L115); connector name dockerhub-mcp is also in dockerhub_api/ontology/mappings/source.yaml. Shape: the fleet name is the pyproject entry point key, resolved by scion_sdk.connector_identity.connector_name; tests/test_fleet_name.py walks IngestBinding and ConnectorContent connector keywords in dockerhub_api. | Every connector name in the package is `dockerhub-mcp`. |

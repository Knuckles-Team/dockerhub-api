# CONN-DOCKERHUB-API-CONNECTOR-CONTENT — Test specification

Governing spec: [spec.md](spec.md).

| Test ID | Requirement | Proving test | Expected observation |
|---|---|---|---|
| T-001 | `CONN-DOCKERHUB-API-CONNECTOR-CONTENT-R001` | `tests/test_default_content_surfaces.py` | The listings include the packaged skills, ontology and prompts. |
| T-003 | `CONN-DOCKERHUB-API-CONNECTOR-CONTENT-R003` | `tests/test_destructive_declaration.py::test_declared_operations_are_destructive_tools_that_ask_first` | Each destructive served tool has `destructiveHint` true and a `confirm` argument and none has `allow_destructive`; a call without `confirm` sends no request, and `confirm=true` sends one. |

## Rows awaiting bound tests
- `CONN-DOCKERHUB-API-CONNECTOR-CONTENT-R002`: planned proof `tests/test_access_contracts.py::test_repository_and_tag_contracts`. Expected: The ttl parses into two contracts whose operations name registered tools and whose columns equal ontology property local names.. Refusal: A contract naming an unregistered tool or a column absent from dockerhub.ttl fails the test..

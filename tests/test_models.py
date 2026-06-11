"""Input/response model behavior."""

import pytest

from dockerhub_api.dockerhub_input_models import (
    AccessTokenCreateModel,
    AuditLogModel,
    BulkInviteModel,
    OrgSettingsModel,
    RepositoryListModel,
    ScimUserListModel,
)
from dockerhub_api.dockerhub_response_models import (
    AccessTokenPage,
    RateLimit,
    Repository,
    ScimListResponse,
    TagPage,
    validate_lenient,
)


def test_pagination_parameters_built():
    model = RepositoryListModel(namespace="acme", page=2, page_size=10)
    assert model.api_parameters == {"page": 2, "page_size": 10}


def test_pagination_bounds_enforced():
    with pytest.raises(ValueError):
        RepositoryListModel(namespace="acme", page=0)
    with pytest.raises(ValueError):
        RepositoryListModel(namespace="acme", page_size=1000)


def test_audit_model_renames_window_params():
    model = AuditLogModel(account="acme", from_date="a", to_date="b")
    assert model.api_parameters is not None
    assert model.api_parameters["from"] == "a"
    assert model.api_parameters["to"] == "b"
    assert "from_date" not in model.api_parameters


def test_org_settings_payload_shape():
    model = OrgSettingsModel(org="acme", restricted_images_enabled=True)
    assert model.payload == {
        "restricted_images": {
            "enabled": True,
            "allow_official_images": True,
            "allow_verified_publishers": True,
        }
    }


def test_scim_params_use_scim_casing():
    model = ScimUserListModel(start_index=1, count=10, sort_by="userName")
    assert model.api_parameters == {
        "startIndex": 1,
        "count": 10,
        "sortBy": "userName",
    }


def test_pat_scope_validation():
    model = AccessTokenCreateModel(
        token_label="ci",
        scopes=["repo:read", "repo:write"],  # nosec B105 B106 — fake test credential
    )
    assert model.payload is not None
    with pytest.raises(ValueError):
        AccessTokenCreateModel(token_label="ci", scopes=[])  # nosec B105 B106 — fake test credential


def test_bulk_invite_payload_includes_dry_run():
    model = BulkInviteModel(org="acme", invitees=["a"], dry_run=True)
    assert model.payload is not None
    assert model.payload["dry_run"] is True


def test_response_models_tolerate_unknown_fields():
    repo = Repository.model_validate(
        {"name": "app", "namespace": "acme", "brand_new_field": 1}
    )
    assert repo.name == "app"
    assert repo.model_dump()["brand_new_field"] == 1


def test_page_models_type_results():
    page = TagPage.model_validate(
        {"count": 1, "results": [{"name": "latest", "full_size": 5}]}
    )
    assert page.results is not None
    assert page.results[0].name == "latest"

    tokens = AccessTokenPage.model_validate(
        {"count": 1, "results": [{"uuid": "u", "token_label": "ci"}]}  # nosec B105 B106 — fake test credential
    )
    assert tokens.results is not None
    assert tokens.results[0].uuid == "u"


def test_scim_list_response_model():
    parsed = ScimListResponse.model_validate(
        {"totalResults": 3, "startIndex": 1, "Resources": [{"id": "x"}]}
    )
    assert parsed.totalResults == 3


def test_rate_limit_model():
    assert RateLimit.model_validate({"limit": 1, "remaining": 0, "reset": 9}).limit == 1


def test_validate_lenient_falls_back_to_raw():
    assert validate_lenient(RateLimit, "not-a-dict") == "not-a-dict"
    assert validate_lenient(RateLimit, None) is None
    assert validate_lenient(RateLimit, {"limit": 5}) == {"limit": 5}

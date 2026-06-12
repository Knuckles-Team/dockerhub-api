"""Registry HTTP API v2 client: scoped-token auth, manifests, blobs, push."""

import httpx
import pytest

from dockerhub_api.api.api_client_base import DestructiveOperationError
from tests.conftest import (
    AMD64_DIGEST,
    CONFIG_DIGEST,
    INDEX_DIGEST,
    REGISTRY_URL,
    MockRegistry,
    make_registry_api,
)


def _registry_paths(registry: MockRegistry) -> list[str]:
    return [r.url.path for r in registry.requests if r.url.host != "auth.docker.io"]


def test_library_normalization(registry, registry_api):
    registry_api.list_tags("nginx")
    assert "/v2/library/nginx/tags/list" in _registry_paths(registry)


def test_list_tags(registry_api):
    result = registry_api.list_tags("library/nginx")
    assert result["status_code"] == 200
    assert result["data"]["tags"] == ["latest", "1.0", "1.1"]


def test_resolve_digest_reads_content_digest_header(registry_api):
    result = registry_api.resolve_digest("nginx", "latest")
    assert result["data"]["digest"] == INDEX_DIGEST
    assert result["data"]["exists"] is True
    assert result["headers"]["Docker-Content-Digest"] == INDEX_DIGEST


def test_get_manifest_returns_index(registry_api):
    result = registry_api.get_manifest("nginx", "latest")
    assert result["data"]["mediaType"].endswith("manifest.list.v2+json")
    assert len(result["data"]["manifests"]) == 2


def test_list_platforms_multiarch(registry_api):
    result = registry_api.list_platforms("nginx", "latest")
    platforms = result["data"]["platforms"]
    arches = {p["architecture"] for p in platforms}
    assert arches == {"amd64", "arm64"}


def test_get_config_follows_index_to_amd64(registry, registry_api):
    result = registry_api.get_config("nginx", "latest")
    assert result["data"]["architecture"] == "amd64"
    assert result["data"]["os"] == "linux"
    # It resolved index -> amd64 child -> config blob.
    paths = _registry_paths(registry)
    assert f"/v2/library/nginx/manifests/{AMD64_DIGEST}" in paths
    assert f"/v2/library/nginx/blobs/{CONFIG_DIGEST}" in paths


def test_inspect_combines_digest_and_platforms(registry_api):
    result = registry_api.inspect("nginx", "latest")
    assert result["data"]["digest"] == INDEX_DIGEST
    assert len(result["data"]["platforms"]) == 2
    assert "config" not in result["data"]


def test_inspect_with_config(registry_api):
    result = registry_api.inspect("nginx", "latest", include_config=True)
    assert result["data"]["config"]["architecture"] == "amd64"


def test_list_referrers(registry_api):
    digest = INDEX_DIGEST
    result = registry_api.list_referrers("nginx", digest)
    manifests = result["data"]["manifests"]
    assert manifests[0]["artifactType"] == "application/vnd.in-toto+json"


def test_check_manifest_and_blob(registry_api):
    assert registry_api.check_manifest("nginx", "latest")["exists"] is True
    assert registry_api.check_blob("nginx", CONFIG_DIGEST)["exists"] is True


# --------------------------- destructive gating --------------------------- #


def test_delete_manifest_gated_by_default(registry_api):
    with pytest.raises(DestructiveOperationError, match="delete_manifest"):
        registry_api.delete_manifest("nginx", "latest")


def test_delete_manifest_resolves_tag_then_deletes(registry, registry_api_destructive):
    result = registry_api_destructive.delete_manifest("nginx", "latest")
    assert result["status_code"] == 202
    paths = _registry_paths(registry)
    # tag resolved to a digest, then DELETE issued against the digest
    assert f"/v2/library/nginx/manifests/{INDEX_DIGEST}" in paths


def test_delete_blob_surfaces_405_cleanly(registry_api_destructive):
    result = registry_api_destructive.delete_blob("nginx", CONFIG_DIGEST)
    assert result["status_code"] == 405


def test_push_session_gated(registry_api):
    with pytest.raises(DestructiveOperationError):
        registry_api.start_upload("myorg/app")
    with pytest.raises(DestructiveOperationError):
        registry_api.put_manifest("myorg/app", "v1", {"schemaVersion": 2}, "media")


def test_full_push_session(registry, registry_api_destructive):
    started = registry_api_destructive.start_upload("myorg/app")
    location = started["headers"]["Location"]
    assert started["status_code"] == 202

    patched = registry_api_destructive.upload_chunk("myorg/app", location, b"layerbytes")
    assert patched["status_code"] == 202

    completed = registry_api_destructive.complete_upload(
        "myorg/app", location, AMD64_DIGEST, final_chunk=b""
    )
    assert completed["status_code"] == 201

    put = registry_api_destructive.put_manifest(
        "myorg/app",
        "v1",
        {"schemaVersion": 2, "mediaType": "x", "config": {}, "layers": []},
        "application/vnd.docker.distribution.manifest.v2+json",
    )
    assert put["status_code"] == 201


def test_mount_blob(registry_api_destructive):
    result = registry_api_destructive.mount_blob("myorg/app", CONFIG_DIGEST, "library/nginx")
    assert result["status_code"] == 201


def test_api_version(registry_api):
    assert registry_api.api_version()["status_code"] == 200


# ------------------------------ token auth -------------------------------- #


def test_token_cached_per_scope(registry, registry_api):
    registry_api.list_tags("nginx")
    registry_api.list_tags("nginx")
    registry_api.list_tags("nginx")
    pull_fetches = [
        f for f in registry.token_fetches if f.get("scope", "").endswith(":pull")
    ]
    # One mint for the shared pull scope, reused across all three calls.
    assert len(pull_fetches) == 1


def test_401_rechallenge_refreshes_token():
    """A stale bearer triggers a WWW-Authenticate re-challenge and one retry."""
    state = {"rejected": False, "mints": 0}

    def transport_handler(request: httpx.Request) -> httpx.Response:
        host = request.url.path
        if request.url.host == "auth.docker.io":
            state["mints"] += 1
            token = f"tok-{state['mints']}"
            return httpx.Response(
                200,
                content=b'{"token": "%s", "expires_in": 300}' % token.encode(),
                headers={"Content-Type": "application/json"},
            )
        auth = request.headers.get("authorization", "")
        # Reject the first token once to force a re-challenge.
        if auth == "Bearer tok-1" and not state["rejected"]:
            state["rejected"] = True
            return httpx.Response(
                401,
                headers={
                    "WWW-Authenticate": (
                        'Bearer realm="https://auth.docker.io/token",'
                        'service="registry.docker.io",'
                        'scope="repository:library/nginx:pull"'
                    )
                },
            )
        return httpx.Response(
            200,
            content=b'{"name": "library/nginx", "tags": ["latest"]}',
            headers={"Content-Type": "application/json"},
        )

    registry = MockRegistry()
    registry.handler = transport_handler  # type: ignore[method-assign]
    api = make_registry_api(registry)
    result = api.list_tags("nginx")
    assert result["status_code"] == 200
    assert state["rejected"] is True
    assert state["mints"] == 2  # initial + post-challenge refresh


def test_registry_base_url(registry_api):
    assert registry_api.url == REGISTRY_URL

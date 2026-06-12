"""Registry HTTP API v2 endpoints (``registry-1.docker.io``).

CONCEPT:HUB-1.7 — Registry v2 client. Image-level operations the Hub
management API does not cover: tag listing, manifest/blob inspection,
multi-arch platform resolution, digest resolution, and (gated) deletes.
CONCEPT:HUB-1.9 — OCI Referrers / attestation discovery.
CONCEPT:HUB-1.10 — chunked blob push (upload session + manifest put).

Pushes, deletes, and blob uploads are destructive and gated by
``allow_destructive`` (``DOCKERHUB_ALLOW_DESTRUCTIVE``). ``_catalog`` is
intentionally omitted: Docker Hub does not support registry-wide catalog
listing (it requires a registry-scoped token the Hub token service won't issue).
"""

import json as _json
from typing import Any

from dockerhub_api.api.api_client_registry_base import (
    ACCEPT_MANIFESTS,
    OCTET_STREAM,
    RegistryApiBase,
)
from dockerhub_api.dockerhub_input_models import (
    RegistryReferrersModel,
    RegistryTagsListModel,
)
from dockerhub_api.dockerhub_response_models import (
    ImageConfig,
    ReferrerList,
    RegistryManifest,
    RegistryTagList,
    validate_lenient,
)

#: Preferred platform when a multi-arch reference must collapse to one image.
_PREFERRED_OS = "linux"
_PREFERRED_ARCH = "amd64"


class RegistryApi(RegistryApiBase):
    """Registry v2: tags, manifests, blobs, referrers, and (gated) push/delete."""

    # ----------------------------- discovery ----------------------------- #

    def api_version(self) -> dict[str, Any]:
        """``GET /v2/`` — verify registry support and authentication."""
        return self._registry_request("GET", None, raise_for_status=False)

    def list_tags(
        self, repo: str, n: int | None = None, last: str | None = None
    ) -> dict[str, Any]:
        """``GET /v2/{repo}/tags/list`` — list a repository's tags."""
        model = RegistryTagsListModel(repo=repo, n=n, last=last)
        envelope = self._registry_request(
            "GET", repo, "/tags/list", params=model.api_parameters
        )
        envelope["data"] = validate_lenient(RegistryTagList, envelope["data"])
        return envelope

    # ----------------------------- manifests ----------------------------- #

    def get_manifest(
        self, repo: str, reference: str, accept: str | None = None
    ) -> dict[str, Any]:
        """``GET /v2/{repo}/manifests/{reference}`` (tag or digest)."""
        envelope = self._registry_request(
            "GET",
            repo,
            f"/manifests/{reference}",
            accept=accept or ACCEPT_MANIFESTS,
        )
        envelope["data"] = validate_lenient(RegistryManifest, envelope["data"])
        return envelope

    def check_manifest(self, repo: str, reference: str) -> dict[str, Any]:
        """``HEAD /v2/{repo}/manifests/{reference}`` — existence + digest."""
        return self._registry_exists(
            repo, f"/manifests/{reference}", accept=ACCEPT_MANIFESTS
        )

    def resolve_digest(self, repo: str, reference: str) -> dict[str, Any]:
        """Resolve a tag/reference to its content-addressable digest."""
        envelope = self._registry_request(
            "HEAD",
            repo,
            f"/manifests/{reference}",
            accept=ACCEPT_MANIFESTS,
            raise_for_status=False,
        )
        digest = envelope.get("headers", {}).get("Docker-Content-Digest")
        envelope["data"] = {
            "reference": reference,
            "digest": digest,
            "media_type": envelope.get("headers", {}).get("Content-Type"),
            "exists": envelope["status_code"] == 200,
        }
        return envelope

    def put_manifest(
        self,
        repo: str,
        reference: str,
        manifest: dict | str,
        media_type: str,
    ) -> dict[str, Any]:
        """``PUT /v2/{repo}/manifests/{reference}`` — push a manifest (gated)."""
        self._guard_destructive("put_manifest")
        body = manifest if isinstance(manifest, str) else _json.dumps(manifest)
        return self._registry_request(
            "PUT",
            repo,
            f"/manifests/{reference}",
            scope_actions="pull,push",
            content=body.encode("utf-8"),
            content_type=media_type,
        )

    def delete_manifest(self, repo: str, reference: str) -> dict[str, Any]:
        """``DELETE /v2/{repo}/manifests/{digest}`` — delete a tag/manifest (gated).

        Docker Hub requires deletion by digest; pass a tag and it is resolved
        to its digest first.
        """
        self._guard_destructive("delete_manifest")
        target = reference
        if not reference.startswith("sha256:"):
            resolved = self.resolve_digest(repo, reference)
            target = resolved["data"].get("digest") or reference
        return self._registry_request(
            "DELETE", repo, f"/manifests/{target}", scope_actions="pull,push,delete"
        )

    # ------------------------------- blobs ------------------------------- #

    def get_blob(self, repo: str, digest: str) -> dict[str, Any]:
        """``GET /v2/{repo}/blobs/{digest}`` — fetch a blob (config/attestation)."""
        return self._registry_request("GET", repo, f"/blobs/{digest}")

    def check_blob(self, repo: str, digest: str) -> dict[str, Any]:
        """``HEAD /v2/{repo}/blobs/{digest}`` — blob existence check."""
        return self._registry_exists(repo, f"/blobs/{digest}")

    def delete_blob(self, repo: str, digest: str) -> dict[str, Any]:
        """``DELETE /v2/{repo}/blobs/{digest}`` — delete a blob (gated).

        Often returns ``405`` on Docker Hub (blob delete disabled); the status
        is surfaced cleanly rather than masked.
        """
        self._guard_destructive("delete_blob")
        return self._registry_request(
            "DELETE",
            repo,
            f"/blobs/{digest}",
            scope_actions="pull,push,delete",
            raise_for_status=False,
        )

    # ------------------------------ referrers ---------------------------- #

    def list_referrers(
        self, repo: str, digest: str, artifact_type: str | None = None
    ) -> dict[str, Any]:
        """``GET /v2/{repo}/referrers/{digest}`` — OCI 1.1 referrers.

        Surfaces SBOM and provenance attestation manifests that reference the
        given image digest as their ``subject``.
        """
        model = RegistryReferrersModel(
            repo=repo, digest=digest, artifact_type=artifact_type
        )
        envelope = self._registry_request(
            "GET",
            repo,
            f"/referrers/{digest}",
            accept="application/vnd.oci.image.index.v1+json",
            params=model.api_parameters,
        )
        envelope["data"] = validate_lenient(ReferrerList, envelope["data"])
        return envelope

    # ---------------------------- convenience ---------------------------- #

    def _resolve_image_manifest(
        self, repo: str, reference: str
    ) -> tuple[dict, str | None]:
        """Return a concrete image manifest dict and its digest.

        Follows one index/manifest-list level, preferring ``linux/amd64``.
        """
        envelope = self.get_manifest(repo, reference)
        manifest = envelope["data"] if isinstance(envelope["data"], dict) else {}
        digest = envelope.get("headers", {}).get("Docker-Content-Digest")
        children = manifest.get("manifests")
        if children:
            chosen = None
            for child in children:
                platform = child.get("platform") or {}
                if (
                    platform.get("os") == _PREFERRED_OS
                    and platform.get("architecture") == _PREFERRED_ARCH
                ):
                    chosen = child
                    break
            chosen = chosen or children[0]
            child_digest = chosen.get("digest")
            if child_digest:
                child_env = self.get_manifest(repo, child_digest)
                if isinstance(child_env["data"], dict):
                    return child_env["data"], child_digest
        return manifest, digest

    def list_platforms(self, repo: str, reference: str) -> dict[str, Any]:
        """Enumerate the platforms a reference resolves to (multi-arch aware)."""
        envelope = self.get_manifest(repo, reference)
        manifest = envelope["data"] if isinstance(envelope["data"], dict) else {}
        platforms: list[dict] = []
        children = manifest.get("manifests")
        if children:
            for child in children:
                platform = child.get("platform") or {}
                platforms.append(
                    {
                        "os": platform.get("os"),
                        "architecture": platform.get("architecture"),
                        "variant": platform.get("variant"),
                        "digest": child.get("digest"),
                        "size": child.get("size"),
                        "mediaType": child.get("mediaType"),
                    }
                )
        else:
            # Single-platform image: derive os/arch from the config blob.
            config = manifest.get("config") or {}
            config_digest = config.get("digest")
            os_name = arch = variant = None
            if config_digest:
                blob = self.get_blob(repo, config_digest)
                if isinstance(blob["data"], dict):
                    os_name = blob["data"].get("os")
                    arch = blob["data"].get("architecture")
                    variant = blob["data"].get("variant")
            platforms.append(
                {
                    "os": os_name,
                    "architecture": arch,
                    "variant": variant,
                    "digest": envelope.get("headers", {}).get("Docker-Content-Digest"),
                    "size": None,
                    "mediaType": manifest.get("mediaType"),
                }
            )
        envelope["data"] = {"platforms": platforms}
        return envelope

    def get_config(self, repo: str, reference: str) -> dict[str, Any]:
        """Fetch the resolved image's config blob (architecture/os/env/history)."""
        manifest, _digest = self._resolve_image_manifest(repo, reference)
        config = manifest.get("config") or {}
        config_digest = config.get("digest")
        if not config_digest:
            return {
                "status_code": 404,
                "data": {"error": "no config descriptor on the resolved manifest"},
                "rate_limit": dict(self.rate_limit),
                "headers": {},
            }
        envelope = self.get_blob(repo, config_digest)
        envelope["data"] = validate_lenient(ImageConfig, envelope["data"])
        return envelope

    def inspect(
        self, repo: str, reference: str, include_config: bool = False
    ) -> dict[str, Any]:
        """``docker buildx imagetools inspect``-style summary of a reference."""
        digest_env = self.resolve_digest(repo, reference)
        platforms_env = self.list_platforms(repo, reference)
        data: dict[str, Any] = {
            "repository": self._normalize_repo(repo),
            "reference": reference,
            "digest": digest_env["data"].get("digest"),
            "media_type": digest_env["data"].get("media_type"),
            "platforms": platforms_env["data"].get("platforms", []),
        }
        if include_config:
            config_env = self.get_config(repo, reference)
            data["config"] = config_env["data"]
        return {
            "status_code": 200,
            "data": data,
            "rate_limit": dict(self.rate_limit),
            "headers": digest_env.get("headers", {}),
        }

    # ------------------------------- push -------------------------------- #

    def start_upload(self, repo: str) -> dict[str, Any]:
        """``POST /v2/{repo}/blobs/uploads/`` — open a blob upload session (gated)."""
        self._guard_destructive("start_upload")
        return self._registry_request(
            "POST", repo, "/blobs/uploads/", scope_actions="pull,push"
        )

    def upload_chunk(
        self,
        repo: str,
        location: str,
        chunk: bytes,
        content_range: str | None = None,
    ) -> dict[str, Any]:
        """``PATCH {location}`` — upload one blob chunk (gated)."""
        self._guard_destructive("upload_chunk")
        extra = {"Content-Range": content_range} if content_range else None
        return self._registry_request(
            "PATCH",
            repo,
            scope_actions="pull,push",
            raw_url=location,
            content=chunk,
            content_type=OCTET_STREAM,
            extra_headers=extra,
        )

    def complete_upload(
        self,
        repo: str,
        location: str,
        digest: str,
        final_chunk: bytes | None = None,
    ) -> dict[str, Any]:
        """``PUT {location}?digest=`` — finalize a blob upload (gated)."""
        self._guard_destructive("complete_upload")
        return self._registry_request(
            "PUT",
            repo,
            scope_actions="pull,push",
            raw_url=location,
            params={"digest": digest},
            content=final_chunk or b"",
            content_type=OCTET_STREAM,
        )

    def mount_blob(self, repo: str, digest: str, from_repo: str) -> dict[str, Any]:
        """``POST /v2/{repo}/blobs/uploads/?mount=&from=`` — cross-repo mount (gated)."""
        self._guard_destructive("mount_blob")
        return self._registry_request(
            "POST",
            repo,
            "/blobs/uploads/",
            scope_actions="pull,push",
            params={"mount": digest, "from": self._normalize_repo(from_repo)},
        )

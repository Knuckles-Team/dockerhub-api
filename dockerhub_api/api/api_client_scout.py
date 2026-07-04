"""Docker Scout API endpoints (``api.scout.docker.com``).

CONCEPT:DH-OS.identity.docker-scout-client-cve — Docker Scout client. CVE / vulnerability, SBOM, and policy
data for images, authenticated with the same Hub JWT minted from
``/v2/auth/token``.

Note on stability: Docker Scout's public REST surface is less formally
specified than the Registry v2 and Hub management APIs. The endpoint templates
below follow Docker Scout's documented structure and are isolated in
``_SCOUT_PATHS`` so they can be corrected in one place if Docker revises them.
Responses are validated leniently (unknown fields ride along; a shape mismatch
falls back to the raw JSON), and endpoints that are gated or unavailable on a
given subscription surface a clean HTTP error envelope rather than raising
opaquely. The base URL is overridable via ``DOCKER_SCOUT_URL``.
"""

from typing import Any

from dockerhub_api.api.api_client_base import DockerHubApiBase
from dockerhub_api.dockerhub_response_models import (
    ScoutImageSummary,
    ScoutPolicyEvaluation,
    ScoutVulnerabilities,
    validate_lenient,
)

#: Endpoint templates, isolated so they track Docker Scout's published API.
_SCOUT_PATHS = {
    "summary": "/v1/orgs/{org}/images/{repo}/summary",
    "cves": "/v1/orgs/{org}/images/{repo}/vulnerabilities",
    "sbom": "/v1/orgs/{org}/images/{repo}/sbom",
    "compare": "/v1/orgs/{org}/images/{repo}/compare",
    "policies": "/v1/orgs/{org}/policies",
    "policy_evaluation": "/v1/orgs/{org}/images/{repo}/policy",
}


class ScoutApi(DockerHubApiBase):
    """Docker Scout: image vulnerability, SBOM, and policy intelligence."""

    @staticmethod
    def _split(repo: str, org: str | None) -> tuple[str, str]:
        """Resolve ``(org, repo_name)`` from a ``namespace/name`` repo + override.

        ``org`` (the Scout-enabled organization namespace) defaults to the
        repository's own namespace when the repo is fully qualified.
        """
        repo = repo.strip("/")
        if org:
            return org, repo
        if "/" in repo:
            namespace, name = repo.split("/", 1)
            return namespace, name
        # Single-segment names belong to the Docker Library namespace.
        return "library", repo

    def _path(self, key: str, repo: str, org: str | None) -> str:
        resolved_org, repo_name = self._split(repo, org)
        return _SCOUT_PATHS[key].format(org=resolved_org, repo=repo_name)

    def get_image_summary(
        self, repo: str, reference: str = "latest", org: str | None = None
    ) -> dict[str, Any]:
        """Vulnerability roll-up and policy posture for an image reference."""
        envelope = self._request(
            "GET", self._path("summary", repo, org), params={"reference": reference}
        )
        envelope["data"] = validate_lenient(ScoutImageSummary, envelope["data"])
        return envelope

    def get_cves(
        self,
        repo: str,
        reference: str = "latest",
        org: str | None = None,
        severity: str | None = None,
    ) -> dict[str, Any]:
        """List CVEs / vulnerabilities affecting an image reference."""
        envelope = self._request(
            "GET",
            self._path("cves", repo, org),
            params={"reference": reference, "severity": severity},
        )
        envelope["data"] = validate_lenient(ScoutVulnerabilities, envelope["data"])
        return envelope

    #: Alias — ``vulnerabilities`` reads more naturally for some callers.
    list_vulnerabilities = get_cves

    def get_sbom(
        self,
        repo: str,
        reference: str = "latest",
        org: str | None = None,
        sbom_format: str | None = None,
    ) -> dict[str, Any]:
        """Fetch the Software Bill of Materials (CycloneDX/SPDX) for an image."""
        return self._request(
            "GET",
            self._path("sbom", repo, org),
            params={"reference": reference, "format": sbom_format},
        )

    def compare(
        self,
        repo: str,
        base_ref: str,
        target_ref: str,
        org: str | None = None,
    ) -> dict[str, Any]:
        """Diff two image references for CVE and policy changes."""
        return self._request(
            "GET",
            self._path("compare", repo, org),
            params={"base": base_ref, "target": target_ref},
        )

    def list_policies(self, org: str) -> dict[str, Any]:
        """List the Scout policies configured for an organization."""
        return self._request("GET", _SCOUT_PATHS["policies"].format(org=org))

    def get_policy_evaluation(
        self, repo: str, reference: str = "latest", org: str | None = None
    ) -> dict[str, Any]:
        """Evaluate an image reference against the org's Scout policies."""
        envelope = self._request(
            "GET",
            self._path("policy_evaluation", repo, org),
            params={"reference": reference},
        )
        envelope["data"] = validate_lenient(ScoutPolicyEvaluation, envelope["data"])
        return envelope

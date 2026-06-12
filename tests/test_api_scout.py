"""Docker Scout client: Hub-JWT reuse, CVE/SBOM/policy endpoints."""


def test_summary(scout_api):
    result = scout_api.get_image_summary("library/nginx", reference="latest")
    assert result["status_code"] == 200
    assert result["data"]["vulnerabilities"]["critical"] == 1


def test_cves(scout, scout_api):
    result = scout_api.get_cves("myorg/app", reference="v1", severity="critical")
    assert result["data"]["cves"][0]["id"] == "CVE-2026-0001"
    # org/repo split → /v1/orgs/myorg/images/app/vulnerabilities
    paths = [r.url.path for r in scout.requests if r.url.host != "hub.docker.com"]
    assert "/v1/orgs/myorg/images/app/vulnerabilities" in paths


def test_vulnerabilities_alias(scout_api):
    result = scout_api.list_vulnerabilities("myorg/app")
    assert result["data"]["cves"]


def test_sbom(scout_api):
    result = scout_api.get_sbom("myorg/app", sbom_format="cyclonedx")
    assert result["data"]["bomFormat"] == "CycloneDX"


def test_compare(scout_api):
    result = scout_api.compare("myorg/app", "v1", "v2")
    assert result["status_code"] == 200
    assert "added" in result["data"]


def test_policies(scout_api):
    result = scout_api.list_policies("myorg")
    assert result["data"]["policies"][0]["id"] == "default"


def test_policy_evaluation(scout_api):
    result = scout_api.get_policy_evaluation("myorg/app", reference="v1")
    assert result["data"]["outcome"] == "passed"


def test_scout_reuses_hub_jwt(scout, scout_api):
    scout_api.get_image_summary("library/nginx")
    scout_api.get_cves("library/nginx")
    # JWT minted once on hub.docker.com, reused for both Scout calls.
    mints = [
        r
        for r in scout.requests
        if r.url.host == "hub.docker.com" and r.url.path == "/v2/auth/token"
    ]
    assert len(mints) == 1

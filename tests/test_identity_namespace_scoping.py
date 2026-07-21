"""Identity-scoped Docker Hub namespace/org auto-load
(CONCEPT:AU-OS.identity.identity-scoped-resource-autoload).

A resolved Docker Hub ``username`` (personal account or org) the caller's
identity is not entitled to is denied before ``get_client``/``get_registry_client``
mint any token. Tests the enforcement logic with the entitlement source
mocked (the resolver itself is tested in agent-utilities).
"""

import pytest

import dockerhub_api.auth as auth_mod


def _entitle(monkeypatch, entitled):
    monkeypatch.setattr(
        auth_mod,
        "_entitled",
        lambda namespace, names: [n for n in names if n in entitled],
    )


def test_get_client_denies_non_entitled_namespace(monkeypatch):
    _entitle(monkeypatch, {"acme-org"})
    monkeypatch.setenv("DOCKERHUB_USERNAME", "other-org")
    monkeypatch.setenv("DOCKERHUB_TOKEN", "dckr_pat_unit")
    with pytest.raises(PermissionError):
        auth_mod.get_client()


def test_get_client_allows_entitled_namespace(monkeypatch):
    _entitle(monkeypatch, {"acme-org"})
    monkeypatch.setenv("DOCKERHUB_USERNAME", "acme-org")
    monkeypatch.setenv("DOCKERHUB_TOKEN", "dckr_pat_unit")
    client = auth_mod.get_client()
    assert client._token_manager.identifier == "acme-org"


def test_get_client_anonymous_skips_entitlement_check(monkeypatch):
    """No resolved identity → nothing to deny (anonymous, public-only client)."""
    _entitle(monkeypatch, set())
    monkeypatch.delenv("DOCKERHUB_USERNAME", raising=False)
    monkeypatch.delenv("DOCKER_HUB_USER", raising=False)
    monkeypatch.delenv("DOCKERHUB_TOKEN", raising=False)
    monkeypatch.delenv("DOCKER_HUB_TOKEN", raising=False)
    client = auth_mod.get_client()
    assert client._token_manager is None


def test_get_registry_client_denies_non_entitled_namespace(monkeypatch):
    _entitle(monkeypatch, {"acme-org"})
    monkeypatch.setenv("DOCKERHUB_USERNAME", "other-org")
    monkeypatch.setenv("DOCKERHUB_TOKEN", "dckr_pat_unit")
    with pytest.raises(PermissionError):
        auth_mod.get_registry_client()


def test_get_registry_client_allows_entitled_namespace(monkeypatch):
    _entitle(monkeypatch, {"acme-org"})
    monkeypatch.setenv("DOCKERHUB_USERNAME", "acme-org")
    monkeypatch.setenv("DOCKERHUB_TOKEN", "dckr_pat_unit")
    client = auth_mod.get_registry_client()
    assert client is not None


def test_missing_resolver_degrades_to_allow(monkeypatch):
    """A broken/absent import of the shared resolver fails open (back-compat)."""
    import builtins

    real_import = builtins.__import__

    def _blocked_import(name, *args, **kwargs):
        if name == "agent_utilities.security.entitlements":
            raise ImportError("simulated: resolver not available")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocked_import)
    assert auth_mod._entitled("dockerhub", ["acme-org"]) == ["acme-org"]

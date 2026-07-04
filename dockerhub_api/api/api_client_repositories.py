"""Repository and tag endpoints (``/v2/namespaces/{ns}/repositories``).

CONCEPT:DH-OS.audit.core-wrapper-api-is — core wrapper. Repository creation is the primary
provisioning use case (creating image repos for releases) and is therefore
*not* destructive-gated.
"""

from typing import Any

from dockerhub_api.api.api_client_base import DockerHubApiBase
from dockerhub_api.dockerhub_input_models import (
    ImmutableTagsPatchModel,
    ImmutableTagsVerifyModel,
    RepositoryCreateModel,
    RepositoryGroupModel,
    RepositoryListModel,
    RepositoryModel,
    TagListModel,
    TagModel,
)
from dockerhub_api.dockerhub_response_models import (
    ImmutableTagsSettings,
    ImmutableTagsVerification,
    Repository,
    RepositoryGroup,
    RepositoryPage,
    Tag,
    TagPage,
    validate_lenient,
)


class DockerHubApiRepositories(DockerHubApiBase):
    """Repositories, tags, immutable tags, and repo-team permissions."""

    def get_repositories(
        self,
        namespace: str,
        name: str | None = None,
        ordering: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        """List a namespace's repositories (name filter + ordering enum)."""
        model = RepositoryListModel(
            namespace=namespace,
            name=name,
            ordering=ordering,
            page=page,
            page_size=page_size,
        )
        envelope = self._request(
            "GET",
            f"/v2/namespaces/{model.namespace}/repositories",
            params=model.api_parameters,
        )
        envelope["data"] = validate_lenient(RepositoryPage, envelope["data"])
        return envelope

    def create_repository(
        self,
        namespace: str,
        name: str,
        description: str | None = None,
        full_description: str | None = None,
        registry: str = "docker",
        is_private: bool = False,
    ) -> dict[str, Any]:
        """Create an image repository in a namespace."""
        model = RepositoryCreateModel(
            namespace=namespace,
            name=name,
            description=description,
            full_description=full_description,
            registry=registry,
            is_private=is_private,
        )
        envelope = self._request(
            "POST",
            f"/v2/namespaces/{model.namespace}/repositories",
            json=model.payload,
        )
        envelope["data"] = validate_lenient(Repository, envelope["data"])
        return envelope

    def get_repository(self, namespace: str, repository: str) -> dict[str, Any]:
        """Get one repository."""
        model = RepositoryModel(namespace=namespace, repository=repository)
        envelope = self._request(
            "GET", f"/v2/namespaces/{model.namespace}/repositories/{model.repository}"
        )
        envelope["data"] = validate_lenient(Repository, envelope["data"])
        return envelope

    def check_repository(self, namespace: str, repository: str) -> dict[str, Any]:
        """HEAD existence check for a repository."""
        model = RepositoryModel(namespace=namespace, repository=repository)
        return self._exists(
            f"/v2/namespaces/{model.namespace}/repositories/{model.repository}"
        )

    # ------------------------------- tags -------------------------------- #

    def get_repository_tags(
        self,
        namespace: str,
        repository: str,
        page: int | None = None,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        """List a repository's tags (paginated)."""
        model = TagListModel(
            namespace=namespace, repository=repository, page=page, page_size=page_size
        )
        envelope = self._request(
            "GET",
            f"/v2/namespaces/{model.namespace}/repositories/{model.repository}/tags",
            params=model.api_parameters,
        )
        envelope["data"] = validate_lenient(TagPage, envelope["data"])
        return envelope

    def check_repository_tags(self, namespace: str, repository: str) -> dict[str, Any]:
        """HEAD check: does the repository have any tags?"""
        model = RepositoryModel(namespace=namespace, repository=repository)
        return self._exists(
            f"/v2/namespaces/{model.namespace}/repositories/{model.repository}/tags"
        )

    def get_repository_tag(
        self, namespace: str, repository: str, tag: str
    ) -> dict[str, Any]:
        """Get one tag."""
        model = TagModel(namespace=namespace, repository=repository, tag=tag)
        envelope = self._request(
            "GET",
            f"/v2/namespaces/{model.namespace}/repositories/{model.repository}"
            f"/tags/{model.tag}",
        )
        envelope["data"] = validate_lenient(Tag, envelope["data"])
        return envelope

    def check_repository_tag(
        self, namespace: str, repository: str, tag: str
    ) -> dict[str, Any]:
        """HEAD existence check for one tag."""
        model = TagModel(namespace=namespace, repository=repository, tag=tag)
        return self._exists(
            f"/v2/namespaces/{model.namespace}/repositories/{model.repository}"
            f"/tags/{model.tag}"
        )

    # --------------------------- immutable tags --------------------------- #

    def update_immutable_tags(
        self,
        namespace: str,
        repository: str,
        enabled: bool,
        rules: list[str] | None = None,
    ) -> dict[str, Any]:
        """Patch a repository's immutable-tags settings."""
        model = ImmutableTagsPatchModel(
            namespace=namespace, repository=repository, enabled=enabled, rules=rules
        )
        envelope = self._request(
            "PATCH",
            f"/v2/namespaces/{model.namespace}/repositories/{model.repository}"
            "/immutabletags",
            json=model.payload,
        )
        envelope["data"] = validate_lenient(ImmutableTagsSettings, envelope["data"])
        return envelope

    def verify_immutable_tags(
        self,
        namespace: str,
        repository: str,
        rules: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Verify immutable-tag rules without applying them."""
        model = ImmutableTagsVerifyModel(
            namespace=namespace, repository=repository, rules=rules, tags=tags
        )
        envelope = self._request(
            "POST",
            f"/v2/namespaces/{model.namespace}/repositories/{model.repository}"
            "/immutabletags/verify",
            json=model.payload,
        )
        envelope["data"] = validate_lenient(ImmutableTagsVerification, envelope["data"])
        return envelope

    # -------------------------- team permissions -------------------------- #

    def assign_repository_group(
        self,
        namespace: str,
        repository: str,
        group_id: int | str,
        permission: str,
    ) -> dict[str, Any]:
        """Grant a team (group) ``read``/``write``/``admin`` on a repository."""
        model = RepositoryGroupModel(
            namespace=namespace,
            repository=repository,
            group_id=group_id,
            permission=permission,
        )
        envelope = self._request(
            "POST",
            f"/v2/repositories/{model.namespace}/{model.repository}/groups",
            json=model.payload,
        )
        envelope["data"] = validate_lenient(RepositoryGroup, envelope["data"])
        return envelope

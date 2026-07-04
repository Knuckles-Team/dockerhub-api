"""The composed Docker Hub API client.

CONCEPT:DH-OS.audit.core-wrapper-api-is — core wrapper. ``Api`` is assembled from per-domain mixins,
all sharing the transport/auth/rate-limit plumbing in
:class:`~dockerhub_api.api.api_client_base.DockerHubApiBase`.
"""

from agent_utilities.base_utilities import get_logger

from dockerhub_api.api.api_client_access_tokens import DockerHubApiAccessTokens
from dockerhub_api.api.api_client_audit_logs import DockerHubApiAuditLogs
from dockerhub_api.api.api_client_auth import DockerHubApiAuth
from dockerhub_api.api.api_client_groups import DockerHubApiGroups
from dockerhub_api.api.api_client_org_access_tokens import DockerHubApiOrgAccessTokens
from dockerhub_api.api.api_client_orgs import DockerHubApiOrgs
from dockerhub_api.api.api_client_registry import RegistryApi
from dockerhub_api.api.api_client_repositories import DockerHubApiRepositories
from dockerhub_api.api.api_client_scim import DockerHubApiScim
from dockerhub_api.api.api_client_scout import ScoutApi

logger = get_logger(__name__)


class Api(
    DockerHubApiAuth,
    DockerHubApiAccessTokens,
    DockerHubApiOrgAccessTokens,
    DockerHubApiAuditLogs,
    DockerHubApiOrgs,
    DockerHubApiRepositories,
    DockerHubApiGroups,
    DockerHubApiScim,
):
    """Full Docker Hub *management* API surface: auth, tokens, repos, orgs,
    teams, audit logs, and SCIM.

    The Registry v2 (:class:`RegistryApi`) and Docker Scout (:class:`ScoutApi`)
    surfaces are separate clients — they target different hosts and auth models
    (per-repository scoped tokens and the Scout API respectively) — and are
    constructed via :func:`dockerhub_api.auth.get_registry_client` /
    :func:`dockerhub_api.auth.get_scout_client`.
    """

    __slots__ = ()


__all__ = ["Api", "RegistryApi", "ScoutApi"]

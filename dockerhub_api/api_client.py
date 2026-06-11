"""The composed Docker Hub API client.

CONCEPT:HUB-1.0 — core wrapper. ``Api`` is assembled from per-domain mixins,
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
from dockerhub_api.api.api_client_repositories import DockerHubApiRepositories
from dockerhub_api.api.api_client_scim import DockerHubApiScim

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
    """Full Docker Hub API surface: auth, tokens, repos, orgs, teams,
    audit logs, and SCIM."""

    __slots__ = ()
